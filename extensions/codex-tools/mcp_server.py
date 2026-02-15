"""
Codex Tools — MCP Server (v0.3.0)

Quantum Symbol Engine (QSE) exposed via stdio JSON-RPC for MOBIUS.
Provides 7-module coherence field validation, Codex Tarot operators,
LOKI phase disruption analysis, glyph integrity checking, and the
15-operator Codex Field Pipeline.

MCP Tools:
  qse_validate_field     — Run full 7-module validation pipeline
  qse_breath_symmetry    — Module 1 only
  qse_emotional_tone     — Module 2 only
  qse_resonance_check    — Module 4 only
  qse_tarot_operator     — Run a Codex Tarot operator (0-21)
  qse_loki_operator      — LOKI phase disruption scan
  qse_glyph_validate     — Validate glyph integrity
  qse_get_state          — Read current QSE state
  qse_operator_status    — Current field pipeline phase and state
  qse_operator_advance   — Advance the pipeline (evaluate + progress)
  qse_operator_activate  — Manually activate protective/amplifier operators
  qse_operator_list      — List all 15 operator definitions

Environment variables:
  COHERENCE_RELAY        — URL of coherence-glove HTTP relay (default: http://127.0.0.1:7777)
  PYTHONUNBUFFERED       — Disable Python output buffering
"""

import sys
import os
import json
import logging
from typing import Any, Dict, Optional
from datetime import datetime

# Force line-buffered stdout for MCP transport
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# Add our own directory for local imports
_self_dir = os.path.dirname(os.path.abspath(__file__))
if _self_dir not in sys.path:
    sys.path.insert(0, _self_dir)

from qse.engine import QSEEngine
from models.state import QSEInputs
from operators.loki import LokiOperator
from operators.glyph_engine import GlyphSandbox
from operators.tarot import TarotOperatorRunner
from operators.field_pipeline import FieldPipeline

logging.basicConfig(
    level=logging.INFO,
    format='[codex-tools] %(levelname)s %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger('codex-tools')

PROTOCOL_VERSION = '2024-11-05'
SERVER_NAME = 'codex-tools'
SERVER_VERSION = '0.3.0'

COHERENCE_RELAY = os.environ.get('COHERENCE_RELAY', 'http://127.0.0.1:7777')

TOOLS = [
    {
        'name': 'qse_validate_field',
        'description': 'Run full 7-module QSE validation: breath symmetry, emotional tone, identity mirror, resonance, amplification, coercion detection, integration. Returns pass/fail per module and overall Σᵣ score.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'breath_data': {
                    'type': 'object',
                    'description': 'Optional breath waveforms: {waveform_1: float[], waveform_2: float[]}',
                },
                'emotional_tokens': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of emotional keywords/phrases to analyze.',
                },
                'identity_assertions': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'List of identity-related statements to check for imposition.',
                },
                'signal_text': {
                    'type': 'string',
                    'description': 'Text to scan for coercion patterns.',
                },
            },
        },
    },
    {
        'name': 'qse_breath_symmetry',
        'description': 'Module 1: Breath symmetry check. B1(t) ≅ B2(t) with 90% alignment threshold.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'waveform_1': {
                    'type': 'array', 'items': {'type': 'number'},
                    'description': 'First breath waveform samples.',
                },
                'waveform_2': {
                    'type': 'array', 'items': {'type': 'number'},
                    'description': 'Second breath waveform samples.',
                },
            },
        },
    },
    {
        'name': 'qse_emotional_tone',
        'description': 'Module 2: Emotional field tone analysis. Detects craving, guilt, nostalgia, fear, anger patterns.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'emotional_tokens': {
                    'type': 'array', 'items': {'type': 'string'},
                    'description': 'Emotional keywords/phrases to analyze.',
                },
            },
            'required': ['emotional_tokens'],
        },
    },
    {
        'name': 'qse_resonance_check',
        'description': 'Module 4: Resonance threshold test. Checks Σᵣ ≥ 0.88.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'signal_metrics': {
                    'type': 'object',
                    'description': 'Signal metrics: {coherence: float, breath_symmetry: float, ...}',
                },
            },
        },
    },
    {
        'name': 'qse_tarot_operator',
        'description': 'Run a Codex Tarot operator (Major Arcana). Each card maps to a QSE checkpoint.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'arcana_id': {
                    'type': 'integer', 'minimum': 0, 'maximum': 21,
                    'description': 'Major Arcana card ID (0=Fool, 1=Magician, ... 21=World).',
                },
            },
            'required': ['arcana_id'],
        },
    },
    {
        'name': 'qse_loki_operator',
        'description': 'LOKI phase disruption scan. Detects cognitive distortions and offers reframes.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'signal_text': {
                    'type': 'string',
                    'description': 'Text to scan for disruption patterns.',
                },
                'context': {
                    'type': 'string',
                    'description': 'Optional context for more accurate analysis.',
                },
            },
            'required': ['signal_text'],
        },
    },
    {
        'name': 'qse_glyph_validate',
        'description': 'Validate Codex glyph integrity. Checks symbols against the 12-glyph catalog.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'glyph_set': {
                    'type': 'array', 'items': {'type': 'string'},
                    'description': 'Unicode glyph symbols to validate.',
                },
            },
            'required': ['glyph_set'],
        },
    },
    {
        'name': 'qse_get_state',
        'description': 'Read current QSE engine state: field phase, validation count, last verdict.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'qse_operator_status',
        'description': 'Get current field pipeline status: phase (VOID through ARCHON), active protections, operator history, field state.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'qse_operator_advance',
        'description': 'Advance the field pipeline. Evaluates the current phase operator and progresses if conditions met. Protective operators (NULLA/SEVERA/SHADRA) can interrupt at any point.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'coherence_score': {
                    'type': 'number',
                    'description': 'Current coherence score (0-1).',
                },
                'emotional_charge': {
                    'type': 'number',
                    'description': 'Current emotional charge level (0-1).',
                },
                'breath_symmetry': {
                    'type': 'number',
                    'description': 'Breath symmetry score (0-1).',
                },
                'resonance_sigma': {
                    'type': 'number',
                    'description': 'Resonance sigma value.',
                },
                'consent_intact': {
                    'type': 'boolean',
                    'description': 'Whether consent architecture is intact.',
                },
                'sovereignty_intact': {
                    'type': 'boolean',
                    'description': 'Whether sovereignty is maintained.',
                },
            },
        },
    },
    {
        'name': 'qse_operator_activate',
        'description': 'Manually activate a protective or amplifier operator. Protective: NULLA (full reset), SEVERA (detachment cut), SHADRA (projection reflector). Amplifiers: HARMONIA (field alignment), AURORA (pattern recognition).',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'operator': {
                    'type': 'string',
                    'description': 'Operator name: NULLA, SEVERA, SHADRA, HARMONIA, or AURORA.',
                },
            },
            'required': ['operator'],
        },
    },
    {
        'name': 'qse_operator_list',
        'description': 'List all 15 Codex Field Operator definitions with name, codex name, cluster, function, glyph, and QSE relevance.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'operator': {
                    'type': 'string',
                    'description': 'Optional: get a single operator by name. Omit to list all 15.',
                },
            },
        },
    },
]


class CodexToolsServer:
    """MCP server exposing QSE tools via stdio JSON-RPC."""

    def __init__(self):
        self.engine = QSEEngine()
        self.loki = LokiOperator()
        self.glyph_sandbox = GlyphSandbox()
        self.tarot = TarotOperatorRunner()
        self.pipeline = FieldPipeline()
        self._initialized = False

        # Try to fetch initial coherence state
        self._fetch_coherence_state()
        log.info('QSE Engine initialized with 7 modules + 15 field operators')

    def _fetch_coherence_state(self):
        """Fetch current state from coherence-glove HTTP relay."""
        try:
            import urllib.request
            token = os.environ.get('BLOOM_RELAY_TOKEN', 'radix-bloom-2026')
            req = urllib.request.Request(
                f'{COHERENCE_RELAY}/state',
                headers={'Authorization': f'Bearer {token}'},
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                state = json.loads(resp.read())
                self.engine.set_coherence_state(state)
                log.info(f'Coherence state loaded: sc={state.get("scalarCoherence", 0):.3f}')
        except Exception as e:
            log.info(f'Coherence relay not available: {e}')

    def handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Handle a single JSON-RPC request."""
        method = request.get('method', '')
        req_id = request.get('id')
        params = request.get('params', {})

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
            'capabilities': {'tools': {}},
            'serverInfo': {'name': SERVER_NAME, 'version': SERVER_VERSION},
        })

    def _handle_tools_list(self, req_id) -> Dict:
        return self._result(req_id, {'tools': TOOLS})

    def _handle_tools_call(self, req_id, params: Dict) -> Dict:
        tool_name = params.get('name', '')
        arguments = params.get('arguments', {})

        try:
            # Refresh coherence state on each tool call
            self._fetch_coherence_state()

            if tool_name == 'qse_validate_field':
                result = self._validate_field(arguments)
            elif tool_name == 'qse_breath_symmetry':
                result = self._breath_symmetry(arguments)
            elif tool_name == 'qse_emotional_tone':
                result = self._emotional_tone(arguments)
            elif tool_name == 'qse_resonance_check':
                result = self._resonance_check(arguments)
            elif tool_name == 'qse_tarot_operator':
                result = self._tarot_operator(arguments)
            elif tool_name == 'qse_loki_operator':
                result = self._loki_operator(arguments)
            elif tool_name == 'qse_glyph_validate':
                result = self._glyph_validate(arguments)
            elif tool_name == 'qse_get_state':
                result = self.engine.get_state()
            elif tool_name == 'qse_operator_status':
                result = self.pipeline.get_status()
            elif tool_name == 'qse_operator_advance':
                result = self.pipeline.advance(arguments or None).to_dict()
            elif tool_name == 'qse_operator_activate':
                result = self.pipeline.activate_operator(
                    arguments.get('operator', ''),
                    arguments,
                ).to_dict()
            elif tool_name == 'qse_operator_list':
                op_name = arguments.get('operator')
                if op_name:
                    result = self.pipeline.get_operator(op_name)
                    if result is None:
                        result = {'error': f'Unknown operator: {op_name}'}
                else:
                    result = self.pipeline.get_operators()
            else:
                return self._error(req_id, -32602, f'Unknown tool: {tool_name}')

            return self._result(req_id, {
                'content': [{'type': 'text', 'text': json.dumps(result, default=str)}],
            })
        except Exception as e:
            log.error(f'Tool call error ({tool_name}): {e}')
            return self._result(req_id, {
                'content': [{'type': 'text', 'text': json.dumps({'error': str(e)})}],
                'isError': True,
            })

    # ── Tool implementations ──

    def _validate_field(self, args: Dict) -> Dict:
        breath = args.get('breath_data', {})
        inputs = QSEInputs(
            breath_waveform_1=breath.get('waveform_1'),
            breath_waveform_2=breath.get('waveform_2'),
            emotional_tokens=args.get('emotional_tokens'),
            identity_assertions=args.get('identity_assertions'),
            signal_text=args.get('signal_text'),
        )
        verdict = self.engine.validate_field(inputs)
        return verdict.to_dict()

    def _breath_symmetry(self, args: Dict) -> Dict:
        inputs = QSEInputs(
            breath_waveform_1=args.get('waveform_1'),
            breath_waveform_2=args.get('waveform_2'),
        )
        result = self.engine.run_single_module('breath_symmetry', inputs)
        if result:
            return {
                'symmetry_pct': result.score,
                'aligned': result.passed,
                'flags': [{'name': f.name, 'severity': f.severity, 'message': f.message}
                          for f in result.flags],
                'details': result.details,
            }
        return {'error': 'Module not found'}

    def _emotional_tone(self, args: Dict) -> Dict:
        inputs = QSEInputs(emotional_tokens=args.get('emotional_tokens', []))
        result = self.engine.run_single_module('emotional_tone', inputs)
        if result:
            return {
                'tone_class': result.details.get('tone_class', 'unknown'),
                'score': result.score,
                'flags': [{'name': f.name, 'severity': f.severity, 'message': f.message}
                          for f in result.flags],
                'details': result.details,
            }
        return {'error': 'Module not found'}

    def _resonance_check(self, args: Dict) -> Dict:
        inputs = QSEInputs(signal_metrics=args.get('signal_metrics'))
        result = self.engine.run_single_module('resonance', inputs)
        if result:
            return {
                'sigma_r': result.score,
                'passes': result.passed,
                'flags': [{'name': f.name, 'severity': f.severity, 'message': f.message}
                          for f in result.flags],
                'details': result.details,
            }
        return {'error': 'Module not found'}

    def _tarot_operator(self, args: Dict) -> Dict:
        arcana_id = args.get('arcana_id', 0)
        coherence = self.engine._coherence_state
        return self.tarot.run(arcana_id, coherence, self.engine.state)

    def _loki_operator(self, args: Dict) -> Dict:
        return self.loki.analyze(
            args.get('signal_text', ''),
            args.get('context'),
        )

    def _glyph_validate(self, args: Dict) -> Dict:
        return self.glyph_sandbox.validate(args.get('glyph_set', []))

    # ── JSON-RPC helpers ──

    @staticmethod
    def _result(req_id, result: Any) -> Dict:
        return {'jsonrpc': '2.0', 'id': req_id, 'result': result}

    @staticmethod
    def _error(req_id, code: int, message: str) -> Dict:
        return {'jsonrpc': '2.0', 'id': req_id, 'error': {'code': code, 'message': message}}


def main():
    """Stdio JSON-RPC event loop."""
    server = CodexToolsServer()
    log.info(f'{SERVER_NAME} v{SERVER_VERSION} started (relay: {COHERENCE_RELAY})')

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                log.error(f'JSON parse error: {e}')
                continue

            response = server.handle_request(request)
            if response is not None:
                sys.stdout.write(json.dumps(response) + '\n')
                sys.stdout.flush()

        except (IOError, OSError):
            break
        except Exception as e:
            log.error(f'Unexpected error: {e}')

    log.info('Server shutting down')


if __name__ == '__main__':
    main()
