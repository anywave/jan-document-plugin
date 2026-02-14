"""
Coherence Glove — MCP Server

Bridges Silver Pancake's MultiWaveCoherenceEngine into MOBIUS via stdio JSON-RPC.
Exposes 5 tools for LLM-initiated coherence measurement:

  coherence_get_state    — current MultiWaveCoherenceState as dict
  coherence_get_consent  — consent level string
  coherence_push_text    — analyze text, push signal, return updated state
  coherence_push_breath  — convert inhale/exhale ms to breath signal
  coherence_reset        — clear engine state

Usage:
  Configured in mcp_config.json as a stdio MCP server.
  PYTHONPATH must include silver-pancake/src for coherence engine imports.
"""

import sys
import json
import logging
import numpy as np
from datetime import datetime
from typing import Any, Dict, Optional

# Silver Pancake coherence engine (via PYTHONPATH)
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
SERVER_VERSION = '0.1.0'

# Engine config — lightweight for text-only mode
ENGINE_CONFIG = EngineConfig(
    window_duration_s=30.0,
    update_interval_s=1.0,
    min_signals=1,
    use_btf=False,  # BTF disabled for text-only mode — no real biometric signals
    adaptive_scheduling=False,
)

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

        # Text → 5-band amplitudes
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
