"""
Coherence Glove — MCP Server (v0.3.0)

Bridges the MultiWave Coherence Engine into MOBIUS via stdio JSON-RPC.
Exposes tools for LLM-initiated coherence measurement, biometric sensor
management, plus an HTTP relay for remote bloom/sensor injection.

MCP Tools:
  coherence_get_state      — current MultiWaveCoherenceState as dict
  coherence_get_consent    — consent level string
  coherence_push_text      — analyze text, push signal, return updated state
  coherence_push_breath    — convert inhale/exhale ms to breath signal
  coherence_start_sensors  — start biometric sensors (microphone, camera)
  coherence_stop_sensors   — stop biometric sensors
  coherence_sensor_status  — check which sensors are running
  coherence_reset          — clear engine state

HTTP Relay (background thread):
  POST /bloom    — push torsion bloom signal (token-authenticated)
  POST /samples  — push raw biometric samples (from breath/PPG sensors)
  GET  /state    — read current coherence state

Environment variables:
  BLOOM_RELAY_PORT   — HTTP relay port (default: 7777, 0 = disabled)
  BLOOM_RELAY_TOKEN  — shared secret for authentication (required for relay)
  PYTHONPATH         — optional path to dev coherence engine source
"""

import sys
import os
import json
import logging
import threading
import signal
import subprocess
import numpy as np
from datetime import datetime
from typing import Any, Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

# Force line-buffered stdout for stdio MCP transport — prevents health check
# timeouts caused by Python's default block-buffering on pipes.
# (stdin is fine because we use readline() which bypasses the iterator buffer.)
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# Bundled Python (._pth) ignores PYTHONPATH — inject it manually
_extra_path = os.environ.get('PYTHONPATH', '')
if _extra_path:
    for p in _extra_path.split(os.pathsep):
        if p and p not in sys.path:
            sys.path.insert(0, p)

# Also add our own directory for vendored packages + text_adapter
_self_dir = os.path.dirname(os.path.abspath(__file__))
if _self_dir not in sys.path:
    sys.path.insert(0, _self_dir)

# Coherence engine (vendored in coherence/ or via PYTHONPATH for dev)
from coherence.engine import create_coherence_engine, EngineConfig
from coherence.scalar_reduction import coherence_to_consent_level

# Local text adapter
from text_adapter import TextCoherenceAdapter

logging.basicConfig(
    level=logging.INFO,
    format='[coherence-glove] %(levelname)s %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger('coherence-glove')

PROTOCOL_VERSION = '2024-11-05'
SERVER_NAME = 'coherence-glove'
SERVER_VERSION = '0.3.0'

# Engine config — supports real biometric signals at 10 Hz
ENGINE_CONFIG = EngineConfig(
    window_duration_s=30.0,
    update_interval_s=1.0,
    min_signals=1,
    use_btf=False,  # BTF disabled — direct coherence computation
    adaptive_scheduling=False,
)

# Biometric sensor config
BIOMETRIC_SAMPLE_RATE = 10.0  # Sensors push at 10 Hz (Nyquist for RAPID φ-band at 3.33 Hz)

# Relay config
BLOOM_RELAY_PORT = int(os.environ.get('BLOOM_RELAY_PORT', '7777'))
BLOOM_RELAY_TOKEN = os.environ.get('BLOOM_RELAY_TOKEN', '')

TOOLS = [
    {
        'name': 'coherence_get_state',
        'description': 'Get current multiwave coherence state including band amplitudes, scalar coherence, intentionality, and dominant band.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_get_consent',
        'description': 'Get current consent level derived from coherence state. Returns FULL_CONSENT, DIMINISHED, SUSPENDED, or EMERGENCY.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_push_text',
        'description': 'Analyze text for coherence markers and push derived signal to the coherence engine. Returns updated state.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'text': {
                    'type': 'string',
                    'description': 'Text to analyze for coherence markers.',
                },
            },
            'required': ['text'],
        },
    },
    {
        'name': 'coherence_push_breath',
        'description': 'Push breath cycle data (inhale and exhale durations) to the coherence engine.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'inhale_ms': {
                    'type': 'number',
                    'description': 'Inhale duration in milliseconds.',
                },
                'exhale_ms': {
                    'type': 'number',
                    'description': 'Exhale duration in milliseconds.',
                },
            },
            'required': ['inhale_ms', 'exhale_ms'],
        },
    },
    {
        'name': 'coherence_start_sensors',
        'description': 'Start biometric sensors for real coherence measurement. Sensors push live data (breath from microphone, pulse from camera) into the coherence engine.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'sensors': {
                    'type': 'array',
                    'items': {'type': 'string', 'enum': ['breath', 'ppg']},
                    'description': 'Which sensors to start. "breath" = microphone breath detection, "ppg" = camera heart rate.',
                },
            },
            'required': ['sensors'],
        },
    },
    {
        'name': 'coherence_stop_sensors',
        'description': 'Stop biometric sensors.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'sensors': {
                    'type': 'array',
                    'items': {'type': 'string', 'enum': ['breath', 'ppg']},
                    'description': 'Which sensors to stop. Omit to stop all.',
                },
            },
        },
    },
    {
        'name': 'coherence_sensor_status',
        'description': 'Check which biometric sensors are currently running.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_reset',
        'description': 'Reset the coherence engine, clearing all accumulated state and stopping sensors.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_session_start',
        'description': 'Start a new coherence session. Auto-ends any active session. Returns session_id.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'coherence_session_end',
        'description': 'End the active coherence session. Persists session data.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'coherence_session_status',
        'description': 'Get current session status: phase, prompt count, CCS trend, model confidence.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'coherence_push_subjective',
        'description': 'Record user subjective coherence score (0-10). Computes divergence from CCS.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'score': {'type': 'number', 'description': 'Subjective coherence score 0-10.', 'minimum': 0, 'maximum': 10},
                'source': {'type': 'string', 'enum': ['mid_session', 'end_session'], 'description': 'When captured.'},
            },
            'required': ['score', 'source'],
        },
    },
    {
        'name': 'coherence_get_scouter_class',
        'description': 'Get SCOUTER destabilization classification: stable, noise, shadow, or trauma.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'coherence_arc_start',
        'description': 'Start a multi-session arc. Bloom suppressed until session 3.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'arc_length': {'type': 'integer', 'description': 'Target sessions in arc.', 'minimum': 2},
                'name': {'type': 'string', 'description': 'Optional arc name.'},
            },
            'required': ['arc_length'],
        },
    },
    {
        'name': 'coherence_arc_status',
        'description': 'Get arc status: completed sessions, CCS/entropy trends, bloom suppression.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'coherence_arc_end',
        'description': 'Manually end the active arc.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
    {
        'name': 'coherence_network_join',
        'description': 'Register this instance as a Kuramoto network node.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'node_id': {'type': 'string', 'description': 'Unique node ID.'},
                'natural_freq': {'type': 'number', 'description': 'Natural oscillation frequency (rad/s).'},
            },
            'required': ['node_id'],
        },
    },
    {
        'name': 'coherence_network_status',
        'description': 'Get network phase coupling status: connected nodes, phase lock score.',
        'inputSchema': {'type': 'object', 'properties': {}},
    },
]


class CoherenceGloveServer:
    """MCP server bridging text/breath/biometric signals to MultiWaveCoherenceEngine."""

    def __init__(self):
        self.engine = create_coherence_engine(
            window_duration_s=ENGINE_CONFIG.window_duration_s,
            update_interval_s=ENGINE_CONFIG.update_interval_s,
            use_btf=ENGINE_CONFIG.use_btf,
        )
        self.adapter = TextCoherenceAdapter()
        self._initialized = False
        self._text_sample_rate = 1.0  # 1 sample per push
        self._breath_sample_rate = 10.0  # synthetic breath signal rate
        self._lock = threading.Lock()  # Protects engine access from relay threads

        # Sensor subprocess management
        self._sensors: Dict[str, subprocess.Popen] = {}
        self._sensor_scripts = {
            'breath': os.path.join(_self_dir, 'breath_sensor.py'),
            'ppg': os.path.join(_self_dir, 'ppg_sensor.py'),
        }

        # Set breath target to φ^-2 (0.382 Hz ≈ 23 BPM) — deep breathing
        # rather than the theoretical φ^-1 (0.618 Hz = 37 BPM) which is
        # faster than any natural human breath rate.
        self.engine.set_breath_target(0.381966)  # φ^-2 = 1/φ²

        # Register a synthetic text stream
        initial_data = np.zeros(5)
        self.engine.register_stream_data(
            'text_coherence', initial_data, self._text_sample_rate
        )
        log.info('Engine initialized with text_coherence stream (breath target=phi^-2=0.382Hz)')

        # Session Intelligence components
        from coherence.session import SessionManager
        from coherence.subjective import SubjectiveTracker
        from coherence.scouter import Scouter
        from coherence.network import KuramotoNetwork, NetworkNode

        sessions_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sessions')
        self.session_mgr = SessionManager(sessions_dir)
        self.subjective = SubjectiveTracker()
        self.scouter = Scouter()
        self.network = KuramotoNetwork()

        # Start HTTP relay for biometric sensors (and optionally bloom injection)
        self._relay_server = None
        if BLOOM_RELAY_PORT > 0:
            self._start_bloom_relay()
            if not BLOOM_RELAY_TOKEN:
                log.info('Bloom relay: /bloom endpoint disabled (no BLOOM_RELAY_TOKEN), /samples open')

    def _start_bloom_relay(self):
        """Start the HTTP bloom relay in a background thread."""
        server_ref = self  # Capture for handler closure

        class BloomHandler(BaseHTTPRequestHandler):
            """HTTP handler for remote bloom injection."""

            def log_message(self, format, *args):
                log.info(f'[relay] {format % args}')

            def _check_token(self) -> bool:
                token = self.headers.get('Authorization', '').replace('Bearer ', '')
                if token != BLOOM_RELAY_TOKEN:
                    self.send_response(401)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'unauthorized'}).encode())
                    return False
                return True

            def do_GET(self):
                if self.path == '/state':
                    if not self._check_token():
                        return
                    state = server_ref._get_state()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(state).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

            def do_POST(self):
                if self.path == '/bloom':
                    if not BLOOM_RELAY_TOKEN:
                        self.send_response(404)
                        self.end_headers()
                        return
                    if not self._check_token():
                        return
                    content_len = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_len)
                    try:
                        data = json.loads(body)
                        result = server_ref._push_bloom(data)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                elif self.path == '/samples':
                    # No auth for /samples — local sensors on localhost
                    content_len = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_len)
                    try:
                        data = json.loads(body)
                        result = server_ref._push_biometric_samples(data)
                        self.send_response(200)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(result).encode())
                    except Exception as e:
                        self.send_response(400)
                        self.send_header('Content-Type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({'error': str(e)}).encode())
                else:
                    self.send_response(404)
                    self.end_headers()

        try:
            self._relay_server = HTTPServer(('0.0.0.0', BLOOM_RELAY_PORT), BloomHandler)
            thread = threading.Thread(target=self._relay_server.serve_forever, daemon=True)
            thread.start()
            log.info(f'Bloom relay listening on port {BLOOM_RELAY_PORT}')
        except OSError as e:
            log.error(f'Failed to start bloom relay: {e}')

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC request."""
        method = request.get('method', '')
        req_id = request.get('id')
        params = request.get('params', {})

        # Notifications (no id) — we don't need to respond
        if req_id is None and method.startswith('notifications/'):
            log.info(f'Notification: {method}')
            return None

        if method == 'initialize':
            return self._handle_initialize(req_id, params)
        elif method == 'tools/list':
            return self._handle_tools_list(req_id)
        elif method == 'tools/call':
            return self._handle_tools_call(req_id, params)
        elif method == 'ping':
            return self._result(req_id, {})
        else:
            return self._error(req_id, -32601, f'Method not found: {method}')

    def _handle_initialize(self, req_id, params: Dict) -> Dict:
        self._initialized = True
        log.info(f'Initialize: protocol={params.get("protocolVersion", "unknown")}')
        return self._result(req_id, {
            'protocolVersion': PROTOCOL_VERSION,
            'capabilities': {
                'tools': {},
            },
            'serverInfo': {
                'name': SERVER_NAME,
                'version': SERVER_VERSION,
            },
        })

    def _handle_tools_list(self, req_id) -> Dict:
        return self._result(req_id, {'tools': TOOLS})

    def _handle_tools_call(self, req_id, params: Dict) -> Dict:
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})

        try:
            if tool_name == 'coherence_get_state':
                result = self._get_state()
            elif tool_name == 'coherence_get_consent':
                result = self._get_consent()
            elif tool_name == 'coherence_push_text':
                result = self._push_text(arguments.get('text', ''))
            elif tool_name == 'coherence_push_breath':
                result = self._push_breath(
                    arguments.get('inhale_ms', 0),
                    arguments.get('exhale_ms', 0),
                )
            elif tool_name == 'coherence_start_sensors':
                result = self._start_sensors(arguments.get('sensors', []))
            elif tool_name == 'coherence_stop_sensors':
                result = self._stop_sensors(arguments.get('sensors'))
            elif tool_name == 'coherence_sensor_status':
                result = self._sensor_status()
            elif tool_name == 'coherence_reset':
                result = self._reset()
            elif tool_name == 'coherence_session_start':
                result = self._session_start()
            elif tool_name == 'coherence_session_end':
                result = self._session_end()
            elif tool_name == 'coherence_session_status':
                result = self.session_mgr.get_status()
            elif tool_name == 'coherence_push_subjective':
                result = self._push_subjective(
                    arguments.get('score', 5.0),
                    arguments.get('source', 'mid_session'),
                )
            elif tool_name == 'coherence_get_scouter_class':
                result = self.scouter.get_status()
            elif tool_name == 'coherence_arc_start':
                result = self._arc_start(
                    arguments.get('arc_length', 9),
                    arguments.get('name'),
                )
            elif tool_name == 'coherence_arc_status':
                result = self.session_mgr.get_arc_status()
            elif tool_name == 'coherence_arc_end':
                result = self._arc_end()
            elif tool_name == 'coherence_network_join':
                result = self._network_join(
                    arguments.get('node_id', ''),
                    arguments.get('natural_freq'),
                )
            elif tool_name == 'coherence_network_status':
                result = self.network.get_status()
            else:
                return self._error(req_id, -32602, f'Unknown tool: {tool_name}')

            return self._result(req_id, {
                'content': [{'type': 'text', 'text': json.dumps(result)}],
            })
        except Exception as e:
            log.error(f'Tool call error ({tool_name}): {e}')
            return self._result(req_id, {
                'content': [{'type': 'text', 'text': json.dumps({'error': str(e)})}],
                'isError': True,
            })

    def _get_state(self) -> Dict:
        """Return current coherence state as dict."""
        with self._lock:
            state = self.engine.get_current_state()
            if state is None:
                return {
                    'active': False,
                    'scalarCoherence': 0.0,
                    'intentionality': 0.0,
                    'breathEntrained': False,
                    'consentLevel': 'SUSPENDED',
                    'bandAmplitudes': [0.0] * 5,
                    'dominantBand': 'CORE',
                    'lastUpdate': None,
                }

            return {
                'active': True,
                'scalarCoherence': float(state.scalar_coherence),
                'intentionality': float(state.intentionality),
                'breathEntrained': bool(state.breath_entrained),
                'consentLevel': self.engine.get_consent_level(),
                'bandAmplitudes': [float(a) for a in state.band_amplitudes],
                'dominantBand': state.dominant_band,
                'lastUpdate': state.timestamp.isoformat(),
            }

    def _get_consent(self) -> Dict:
        """Return current consent level."""
        with self._lock:
            state = self.engine.get_current_state()
            if state is None:
                return {'consentLevel': 'SUSPENDED', 'scalarCoherence': 0.0}

            return {
                'consentLevel': self.engine.get_consent_level(),
                'scalarCoherence': float(state.scalar_coherence),
            }

    def _push_text(self, text: str) -> Dict:
        """Analyze text and push derived signal to engine."""
        if not text:
            return {'error': 'Empty text', 'state': self._get_state()}

        # Text -> 5-band amplitudes (adapter is main-thread only, no lock needed)
        amplitudes = self.adapter.analyze(text)
        smoothed = self.adapter.get_smoothed()

        with self._lock:
            self.engine.push_samples('text_coherence', smoothed)
            self.engine.process_window()

        # Track prompt in session
        self.session_mgr.record_prompt(token_count=len(text.split()) * 2)

        # Update SCOUTER and session CCS
        with self._lock:
            current = self.engine.get_current_state()
            if current:
                classification = self.scouter.classify(current)
                self.session_mgr.record_ccs(current.scalar_coherence)
                from coherence.scouter import DestabilizationClass
                if (classification != DestabilizationClass.STABLE and
                        self.session_mgr.active_session):
                    scouter_events = self.session_mgr.active_session.metadata.setdefault(
                        'scouter_events', []
                    )
                    scouter_events.append(self.scouter.get_status())

        state = self._get_state()
        state['textBands'] = {
            'raw': [float(a) for a in amplitudes],
            'smoothed': [float(a) for a in smoothed],
        }
        return state

    def _push_breath(self, inhale_ms: float, exhale_ms: float) -> Dict:
        """Convert breath cycle to signal and push to engine."""
        if inhale_ms <= 0 or exhale_ms <= 0:
            return {'error': 'Invalid breath durations'}

        # Compute breath metrics
        total_ms = inhale_ms + exhale_ms
        breath_hz = 1000.0 / total_ms  # cycles per second

        # Symmetry (0-1): how balanced is inhale vs exhale
        longer = max(inhale_ms, exhale_ms)
        shorter = min(inhale_ms, exhale_ms)
        symmetry = shorter / longer

        # Generate synthetic breath waveform (one cycle at sample_rate)
        n_samples = int(self._breath_sample_rate * (total_ms / 1000.0))
        n_samples = max(4, n_samples)

        # Inhale phase (rising) + exhale phase (falling)
        inhale_frac = inhale_ms / total_ms
        n_inhale = max(1, int(n_samples * inhale_frac))
        n_exhale = n_samples - n_inhale

        inhale_wave = np.linspace(0, symmetry, n_inhale)
        exhale_wave = np.linspace(symmetry, 0, n_exhale)
        breath_signal = np.concatenate([inhale_wave, exhale_wave])

        with self._lock:
            try:
                self.engine.push_samples('breath', breath_signal)
            except (KeyError, ValueError):
                self.engine.register_stream_data(
                    'breath', breath_signal, self._breath_sample_rate
                )
            self.engine.process_window()

        state = self._get_state()
        state['breathMetrics'] = {
            'breathHz': round(breath_hz, 4),
            'symmetry': round(symmetry, 4),
            'inhaleMs': inhale_ms,
            'exhaleMs': exhale_ms,
        }
        return state

    def _push_bloom(self, data: Dict) -> Dict:
        """Push remote torsion bloom signal into the engine.

        Accepts band amplitudes directly (from RADIX's session) and
        injects them as a coherence signal, merging with local state.

        Expected data format:
          bandAmplitudes: [5] floats (ULTRA, SLOW, CORE, FAST, RAPID)
          intentionality: float 0-1 (optional, defaults to 1.0)
          source: string identifier (optional)
        """
        band_amps = data.get('bandAmplitudes')
        if not band_amps or len(band_amps) != 5:
            return {'error': 'bandAmplitudes must be array of 5 floats'}

        amplitudes = np.array(band_amps, dtype=np.float64)
        amplitudes = np.clip(amplitudes, 0.0, 1.0)

        with self._lock:
            try:
                self.engine.push_samples('bloom_relay', amplitudes)
            except (KeyError, ValueError):
                self.engine.register_stream_data(
                    'bloom_relay', amplitudes, 1.0
                )
            self.engine.process_window()

        state = self._get_state()
        state['bloomSource'] = data.get('source', 'remote')
        state['bloomInjected'] = True
        log.info(f'Bloom injected from {data.get("source", "remote")}: '
                 f'coherence={state["scalarCoherence"]:.3f}')
        return state

    def _push_biometric_samples(self, data: Dict) -> Dict:
        """Push raw biometric samples from sensors into the engine.

        Expected data format:
          stream: string — stream name (breath, ppg_finger, ppg_face)
          samples: [float, ...] — time-series values
          sample_rate: float — samples per second (typically 10.0)
          source: string — identifier (optional)
        """
        stream_name = data.get('stream')
        samples = data.get('samples')
        sample_rate = data.get('sample_rate', BIOMETRIC_SAMPLE_RATE)

        if not stream_name or not samples:
            return {'error': 'stream and samples are required'}

        samples_arr = np.array(samples, dtype=np.float64)

        with self._lock:
            try:
                self.engine.push_samples(stream_name, samples_arr)
            except (KeyError, ValueError):
                # First push for this stream — register it
                self.engine.register_stream_data(
                    stream_name, samples_arr, sample_rate
                )
            self.engine.process_window()

        state = self._get_state()
        state['biometricSource'] = {
            'stream': stream_name,
            'samplesReceived': len(samples),
            'sampleRate': sample_rate,
            'source': data.get('source', 'unknown'),
        }
        return state

    def _start_sensors(self, sensors: List[str]) -> Dict:
        """Start biometric sensor subprocesses."""
        results = {}
        python_exe = sys.executable  # Use same Python that runs MCP server

        for sensor_name in sensors:
            if sensor_name not in self._sensor_scripts:
                results[sensor_name] = {'error': f'Unknown sensor: {sensor_name}'}
                continue

            # Check if already running
            if sensor_name in self._sensors:
                proc = self._sensors[sensor_name]
                if proc.poll() is None:
                    results[sensor_name] = {'status': 'already_running', 'pid': proc.pid}
                    continue
                # Dead process — clean up
                del self._sensors[sensor_name]

            script = self._sensor_scripts[sensor_name]
            if not os.path.exists(script):
                results[sensor_name] = {'error': f'Script not found: {script}'}
                continue

            cmd = [
                python_exe, script,
                '--port', str(BLOOM_RELAY_PORT),
                '--token', BLOOM_RELAY_TOKEN,
            ]

            try:
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
                )
                self._sensors[sensor_name] = proc
                results[sensor_name] = {'status': 'started', 'pid': proc.pid}
                log.info(f'Sensor {sensor_name} started (PID {proc.pid})')
            except Exception as e:
                results[sensor_name] = {'error': str(e)}
                log.error(f'Failed to start sensor {sensor_name}: {e}')

        return {'sensors': results}

    def _stop_sensors(self, sensors: Optional[List[str]] = None) -> Dict:
        """Stop biometric sensor subprocesses."""
        targets = sensors if sensors else list(self._sensors.keys())
        results = {}

        for sensor_name in targets:
            if sensor_name not in self._sensors:
                results[sensor_name] = {'status': 'not_running'}
                continue

            proc = self._sensors[sensor_name]
            if proc.poll() is not None:
                del self._sensors[sensor_name]
                results[sensor_name] = {'status': 'already_stopped'}
                continue

            try:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=2)
                del self._sensors[sensor_name]
                results[sensor_name] = {'status': 'stopped'}
                log.info(f'Sensor {sensor_name} stopped')
            except Exception as e:
                results[sensor_name] = {'error': str(e)}
                log.error(f'Failed to stop sensor {sensor_name}: {e}')

        return {'sensors': results}

    def _sensor_status(self) -> Dict:
        """Check which sensors are running."""
        status = {}
        for name, proc in list(self._sensors.items()):
            if proc.poll() is None:
                status[name] = {'running': True, 'pid': proc.pid}
            else:
                status[name] = {'running': False, 'exitCode': proc.returncode}
                del self._sensors[name]

        # List available sensors
        available = []
        for name, script in self._sensor_scripts.items():
            available.append({
                'name': name,
                'script': script,
                'exists': os.path.exists(script),
                'running': name in self._sensors,
            })

        return {'active': status, 'available': available}

    def _reset(self) -> Dict:
        """Reset engine, adapter, and stop sensors."""
        # Stop all sensors first
        self._stop_sensors()

        with self._lock:
            self.engine.reset()
            self.adapter.reset()
            initial_data = np.zeros(5)
            self.engine.register_stream_data(
                'text_coherence', initial_data, self._text_sample_rate
            )

        log.info('Engine, adapter, and sensors reset')
        return {'reset': True, 'state': self._get_state()}

    def _session_start(self) -> Dict:
        session = self.session_mgr.start_session()
        self.subjective.reset_session()
        log.info(f'Session started: {session.session_id}')
        return {'session_id': session.session_id, 'phase': session.phase.value}

    def _session_end(self) -> Dict:
        session = self.session_mgr.end_session()
        if session is None:
            return {'error': 'No active session'}
        log.info(f'Session ended: {session.session_id}')
        return session.to_dict()

    def _push_subjective(self, score: float, source: str) -> Dict:
        session = self.session_mgr.active_session
        if session is None:
            return {'error': 'No active session'}
        with self._lock:
            ccs_state = self.engine.get_current_state()
            ccs_val = ccs_state.scalar_coherence if ccs_state else 0.0
        entry = self.subjective.record(session.session_id, score, source, ccs_val)
        session.metadata['subjective_score'] = score
        session.metadata['model_confidence'] = self.subjective.model_confidence()
        return entry.to_dict()

    def _arc_start(self, arc_length: int, name: Optional[str] = None) -> Dict:
        arc = self.session_mgr.start_arc(arc_length, name)
        log.info(f'Arc started: {arc.arc_id} (length={arc_length})')
        return arc.to_dict()

    def _arc_end(self) -> Dict:
        arc = self.session_mgr.end_arc()
        if arc is None:
            return {'error': 'No active arc'}
        return arc.to_dict()

    def _network_join(self, node_id: str, natural_freq: Optional[float] = None) -> Dict:
        if not node_id:
            return {'error': 'node_id is required'}
        from coherence.network import NetworkNode
        node = NetworkNode(node_id=node_id, phase=0.0, natural_freq=natural_freq or 0.1, ccs=0.0)
        self.network.add_node(node)
        log.info(f'Network node joined: {node_id}')
        return self.network.get_status()

    @staticmethod
    def _result(req_id, result: Any) -> Dict:
        return {'jsonrpc': '2.0', 'id': req_id, 'result': result}

    @staticmethod
    def _error(req_id, code: int, message: str) -> Dict:
        return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': code, 'message': message}}


def main():
    """Run MCP server on stdio.

    Uses readline() instead of `for line in sys.stdin:` to avoid Python's
    read-ahead buffering on pipes, which can cause the process to appear
    unresponsive to MCP health checks (list_all_tools with 2s timeout).
    """
    # Ignore SIGPIPE/broken pipe — let the read loop detect EOF instead
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    server = CoherenceGloveServer()
    log.info('Coherence Glove MCP server started')

    while True:
        try:
            line = sys.stdin.readline()
        except (IOError, OSError):
            # Broken pipe or stdin closed
            break

        if not line:
            # EOF — parent process closed stdin
            break

        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            response = {
                'jsonrpc': '2.0',
                'id': None,
                'error': {'code': -32700, 'message': f'Parse error: {e}'},
            }
            try:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()
            except (IOError, OSError):
                break
            continue

        response = server.handle_request(request)
        if response is not None:
            try:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()
            except (IOError, OSError):
                # stdout closed — parent process gone
                break

    log.info('Coherence Glove MCP server stopped')


if __name__ == '__main__':
    main()
