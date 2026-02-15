"""
Codex Field Operators — 15 operators across 7 clusters.

The operator stack governs the coherence field lifecycle:

Sequential flow:
  VOID -> PRIMA -> VECTIS -> SIGMA -> LIMITA -> CALYPSO ->
  MORPHIS -> SYNTARA -> LUXIS -> INTEGRIA -> ARCHON

Protective mutex (side channels):
  NULLA  — Zero-point reset (coercion/destabilization)
  SEVERA — Detachment cut (sovereignty compromise)
  SHADRA — Projection reflector (archetypal inflation)

Coherence amplifiers:
  HARMONIA — Multi-layer field alignment
  AURORA   — Emergent pattern recognition
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class OperatorCluster(Enum):
    """The 7 operator clusters."""
    PRE_ACCUMULATION = "pre_accumulation"
    ACCUMULATION_STABILIZER = "accumulation_stabilizer"
    TRANSITION = "transition"
    EXPRESSION = "expression"
    POST_EXPRESSION = "post_expression"
    PROTECTIVE_MUTEX = "protective_mutex"
    COHERENCE_AMPLIFIER = "coherence_amplifier"


class OperatorPhase(Enum):
    """Pipeline phases corresponding to sequential operators."""
    VOID = "void"
    PRIMA = "prima"
    VECTIS = "vectis"
    SIGMA = "sigma"
    LIMITA = "limita"
    CALYPSO = "calypso"
    MORPHIS = "morphis"
    SYNTARA = "syntara"
    LUXIS = "luxis"
    INTEGRIA = "integria"
    ARCHON = "archon"


# Ordered sequence for pipeline progression
PHASE_SEQUENCE = [
    OperatorPhase.VOID,
    OperatorPhase.PRIMA,
    OperatorPhase.VECTIS,
    OperatorPhase.SIGMA,
    OperatorPhase.LIMITA,
    OperatorPhase.CALYPSO,
    OperatorPhase.MORPHIS,
    OperatorPhase.SYNTARA,
    OperatorPhase.LUXIS,
    OperatorPhase.INTEGRIA,
    OperatorPhase.ARCHON,
]


@dataclass
class OperatorResult:
    """Result of evaluating an operator against the current field state."""
    operator: str
    activated: bool
    score: float  # 0.0 to 1.0
    message: str
    flags: List[str] = field(default_factory=list)
    field_mutations: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'operator': self.operator,
            'activated': self.activated,
            'score': self.score,
            'message': self.message,
            'flags': self.flags,
            'field_mutations': self.field_mutations,
        }


@dataclass
class FieldState:
    """Current state of the coherence field.

    Tracks accumulation levels, consent status, breath data,
    emotional charge, and operator history.
    """
    phase: OperatorPhase = OperatorPhase.VOID
    intent_set: bool = False
    direction_locked: bool = False
    sigma_accumulated: float = 0.0
    structural_capacity: float = 1.0
    concealment_stable: bool = False
    restructured: bool = False
    bloom_expressed: bool = False
    radiance_level: float = 0.0
    integrated: bool = False
    encoded: bool = False

    # Protective states
    consent_intact: bool = True
    sovereignty_intact: bool = True
    projection_detected: bool = False
    coercion_detected: bool = False

    # Coherence amplifier states
    breath_aligned: bool = False
    emotion_aligned: bool = False
    logic_aligned: bool = False
    somatic_grounded: bool = False
    new_pattern_detected: bool = False

    # Metrics from QSE / coherence engine
    coherence_score: float = 0.0
    emotional_charge: float = 0.0
    breath_symmetry: float = 0.0
    resonance_sigma: float = 0.0

    # History
    operator_history: List[str] = field(default_factory=list)
    active_protections: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'phase': self.phase.value,
            'intent_set': self.intent_set,
            'direction_locked': self.direction_locked,
            'sigma_accumulated': self.sigma_accumulated,
            'structural_capacity': self.structural_capacity,
            'concealment_stable': self.concealment_stable,
            'restructured': self.restructured,
            'bloom_expressed': self.bloom_expressed,
            'radiance_level': self.radiance_level,
            'integrated': self.integrated,
            'encoded': self.encoded,
            'consent_intact': self.consent_intact,
            'sovereignty_intact': self.sovereignty_intact,
            'projection_detected': self.projection_detected,
            'coercion_detected': self.coercion_detected,
            'breath_aligned': self.breath_aligned,
            'emotion_aligned': self.emotion_aligned,
            'logic_aligned': self.logic_aligned,
            'somatic_grounded': self.somatic_grounded,
            'new_pattern_detected': self.new_pattern_detected,
            'coherence_score': self.coherence_score,
            'emotional_charge': self.emotional_charge,
            'breath_symmetry': self.breath_symmetry,
            'resonance_sigma': self.resonance_sigma,
            'operator_history': self.operator_history,
            'active_protections': self.active_protections,
        }


# ── Operator Definitions ────────────────────────────────────────────

@dataclass
class OperatorDef:
    """Static definition of an operator."""
    name: str
    codex_name: str
    cluster: OperatorCluster
    function: str
    glyph: str
    qse_relevance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'codex_name': self.codex_name,
            'cluster': self.cluster.value,
            'function': self.function,
            'glyph': self.glyph,
            'qse_relevance': self.qse_relevance,
        }


# All 15 operators
OPERATORS: Dict[str, OperatorDef] = {
    'PRIMA': OperatorDef(
        name='PRIMA',
        codex_name='Initiation Seed',
        cluster=OperatorCluster.PRE_ACCUMULATION,
        function='Establishes the first micro-vector of intent before measurable accumulation begins.',
        glyph='◈',
    ),
    'VECTIS': OperatorDef(
        name='VECTIS',
        codex_name='Directional Lock',
        cluster=OperatorCluster.PRE_ACCUMULATION,
        function='Defines trajectory of accumulation. Without VECTIS, Sigma becomes chaotic hoarding.',
        glyph='⟐',
    ),
    'SIGMA': OperatorDef(
        name='SIGMA',
        codex_name='Accumulation',
        cluster=OperatorCluster.ACCUMULATION_STABILIZER,
        function='Accumulation of emotional charge, insight, resonance, coherence amplitude. Must be bounded.',
        glyph='Σ',
    ),
    'LIMITA': OperatorDef(
        name='LIMITA',
        codex_name='Threshold Governor',
        cluster=OperatorCluster.ACCUMULATION_STABILIZER,
        function='Prevents Sigma from exceeding structural capacity. Protects against emotional flooding and identity distortion.',
        glyph='⊘',
        qse_relevance='Prevents emotional overflow',
    ),
    'CALYPSO': OperatorDef(
        name='CALYPSO',
        codex_name='Concealment Incubator',
        cluster=OperatorCluster.TRANSITION,
        function='Stabilizes the liminal interval. Prevents premature bloom. Protects consent architecture.',
        glyph='◐',
    ),
    'MORPHIS': OperatorDef(
        name='MORPHIS',
        codex_name='Structural Reorganization',
        cluster=OperatorCluster.TRANSITION,
        function='Rewrites internal configuration before bloom. Without MORPHIS, bloom reproduces old patterns.',
        glyph='⟳',
    ),
    'SYNTARA': OperatorDef(
        name='SYNTARA',
        codex_name='Bloom',
        cluster=OperatorCluster.EXPRESSION,
        function='Stable, integrated expression of accumulated and incubated coherence. Not impulse, not discharge, but integrated articulation.',
        glyph='✦',
    ),
    'LUXIS': OperatorDef(
        name='LUXIS',
        codex_name='Radiant Amplifier',
        cluster=OperatorCluster.EXPRESSION,
        function='Amplifies bloom outward into network. Used carefully, otherwise becomes ego inflation.',
        glyph='☀',
    ),
    'INTEGRIA': OperatorDef(
        name='INTEGRIA',
        codex_name='Assimilation Field',
        cluster=OperatorCluster.POST_EXPRESSION,
        function='Reintegrates bloom into identity structure. Prevents afterglow distortion, memory looping, attachment overgrowth.',
        glyph='⊕',
        qse_relevance='Ensures afterglow stabilizes',
    ),
    'ARCHON': OperatorDef(
        name='ARCHON',
        codex_name='Memory Encoding',
        cluster=OperatorCluster.POST_EXPRESSION,
        function='Encodes the event into the memory grid. Determines whether it becomes wisdom or obsession.',
        glyph='⊙',
    ),
    'NULLA': OperatorDef(
        name='NULLA',
        codex_name='Zero-Point Reset',
        cluster=OperatorCluster.PROTECTIVE_MUTEX,
        function='Full field neutralization. Activated when coercion detected, overprojection occurs, or emotional destabilization. Equivalent to Silence Gate at systemic level.',
        glyph='⊗',
    ),
    'SEVERA': OperatorDef(
        name='SEVERA',
        codex_name='Detachment Cut',
        cluster=OperatorCluster.PROTECTIVE_MUTEX,
        function='Cuts entanglement threads. Activates when sovereignty compromised or consent architecture fractured.',
        glyph='✂',
        qse_relevance='Cuts unhealthy attachment loops',
    ),
    'SHADRA': OperatorDef(
        name='SHADRA',
        codex_name='Projection Reflector',
        cluster=OperatorCluster.PROTECTIVE_MUTEX,
        function='Reflects unintegrated archetypes back to sender. Protects QSE from twin flame inflation, destiny overlays, mythic entrapment.',
        glyph='◇',
        qse_relevance='Reflects archetypal projections',
    ),
    'HARMONIA': OperatorDef(
        name='HARMONIA',
        codex_name='Field Alignment',
        cluster=OperatorCluster.COHERENCE_AMPLIFIER,
        function='Synchronizes multi-layer coherence: breath, emotion, logic, somatic grounding. Often required before SYNTARA.',
        glyph='≋',
        qse_relevance='Aligns breath-emotion-logic coherence before bloom',
    ),
    'AURORA': OperatorDef(
        name='AURORA',
        codex_name='Emergent Pattern Recognition',
        cluster=OperatorCluster.COHERENCE_AMPLIFIER,
        function='Detects when a new structural pattern has formed. Prevents repeating old relational templates.',
        glyph='✧',
    ),
}
