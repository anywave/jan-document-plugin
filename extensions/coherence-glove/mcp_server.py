"""
Coherence Glove — MCP Server

Bridges the MultiWave Coherence Engine into MOBIUS via stdio JSON-RPC.
Exposes 5 tools for LLM-initiated coherence measurement, plus an HTTP
relay for remote bloom injection.

MCP Tools:
  coherence_get_state    — current MultiWaveCoherenceState as dict
  coherence_get_consent  — consent level string
  coherence_push_text    — analyze text, push signal, return updated state
  coherence_push_breath  — convert inhale/exhale ms to breath signal
  coherence_reset        — clear engine state

HTTP Relay (background thread):
  POST /bloom  — push torsion bloom signal (token-authenticated)
  GET  /state  — read current coherence state

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
import numpy as np
from datetime import datetime
from typing import Any, Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler

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
SERVER_VERSION = '0.2.0'

# Engine config — lightweight for text-only mode
ENGINE_CONFIG = EngineConfig(
    window_duration_s=30.0,
    update_interval_s=1.0,
    min_signals=1,
    use_btf=False,  # BTF disabled for text-only mode — no real biometric signals
    adaptive_scheduling=False,
)

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
        'name': 'coherence_reset',
        'description': 'Reset the coherence engine, clearing all accumulated state.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
]


class CoherenceGloveServer:
    """MCP server bridging text/breath signals to MultiWaveCoherenceEngine."""

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

        # Register a synthetic text stream
        initial_data = np.zeros(5)
        self.engine.register_stream_data(
            'text_coherence', initial_data, self._text_sample_rate
        )
        log.info('Engine initialized with text_coherence stream')

        # Start HTTP bloom relay if configured
        self._relay_server = None
        if BLOOM_RELAY_PORT > 0 and BLOOM_RELAY_TOKEN:
            self._start_bloom_relay()
        elif BLOOM_RELAY_PORT > 0 and not BLOOM_RELAY_TOKEN:
            log.info('Bloom relay disabled: BLOOM_RELAY_TOKEN not set')

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
            elif tool_name == 'coherence_reset':
                result = self._reset()
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

        # Text -> 5-band amplitudes
        amplitudes = self.adapter.analyze(text)
        smoothed = self.adapter.get_smoothed()

        # Push smoothed amplitudes as a new sample to the text stream
        self.engine.push_samples('text_coherence', smoothed)

        # Process window to update state
        self.engine.process_window()

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

        # Register or push breath stream
        try:
            self.engine.push_samples('breath', breath_signal)
        except (KeyError, ValueError):
            # First breath push — register the stream
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

        # Register or push bloom stream
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

    def _reset(self) -> Dict:
        """Reset engine and adapter."""
        self.engine.reset()
        self.adapter.reset()

        # Re-register text stream after reset
        initial_data = np.zeros(5)
        self.engine.register_stream_data(
            'text_coherence', initial_data, self._text_sample_rate
        )

        log.info('Engine and adapter reset')
        return {'reset': True, 'state': self._get_state()}

    @staticmethod
    def _result(req_id, result: Any) -> Dict:
        return {'jsonrpc': '2.0', 'id': req_id, 'result': result}

    @staticmethod
    def _error(req_id, code: int, message: str) -> Dict:
        return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': code, 'message': message}}


def main():
    """Run MCP server on stdio."""
    server = CoherenceGloveServer()
    log.info('Coherence Glove MCP server started')

    for line in sys.stdin:
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
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()
            continue

        response = server.handle_request(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + '\n')
            sys.stdout.flush()

    log.info('Coherence Glove MCP server stopped')


if __name__ == '__main__':
    main()
