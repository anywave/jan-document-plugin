"""Codex Tarot — 22 Major Arcana as QSE operator definitions."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TarotArcanum:
    """A Major Arcana card mapped to a QSE operator checkpoint."""
    id: int  # 0-21
    name: str
    codex_name: str  # Codex-specific naming
    glyph: str  # Associated Unicode glyph
    qse_role: str  # What this operator validates in QSE
    phase: str  # Which QSE module phase it maps to
    description: str
    operator_prompt: str  # The prompt template for this operator


MAJOR_ARCANA: List[TarotArcanum] = [
    TarotArcanum(0, 'The Fool', 'ZERO_POINT', '◊',
                 'Initial state validation — field at zero-point',
                 'pre-validation',
                 'The beginning before breath. No assumptions, no phase.',
                 'Validate that the field is in a clean zero-point state before validation begins.'),
    TarotArcanum(1, 'The Magician', 'OPERATOR_ACTIVE', 'Ξ',
                 'Operator activation — field responsive to intent',
                 'breath_symmetry',
                 'The field responds to conscious intent. Breath initiates.',
                 'Confirm the operator (user) has activated intentional engagement with the field.'),
    TarotArcanum(2, 'The High Priestess', 'INNER_KNOWING', 'ψ',
                 'Intuitive alignment — psi-loop integrity',
                 'breath_symmetry',
                 'The unconscious field speaks. Listen before acting.',
                 'Check psi-loop integrity: is the observer function stable and self-referencing?'),
    TarotArcanum(3, 'The Empress', 'FIELD_NURTURE', 'φ',
                 'Field nourishment — golden ratio presence',
                 'emotional_tone',
                 'The field is fertile. Coherence grows from care, not force.',
                 'Verify emotional field supports growth rather than extraction.'),
    TarotArcanum(4, 'The Emperor', 'FIELD_STRUCTURE', 'Σ',
                 'Structural integrity — resonance boundaries',
                 'emotional_tone',
                 'Structure without rigidity. Boundaries that breathe.',
                 'Confirm resonance boundaries are set but not brittle.'),
    TarotArcanum(5, 'The Hierophant', 'TEACHING_GATE', 'μ',
                 'Knowledge transmission — mutex integrity',
                 'identity_mirror',
                 'True teaching holds paradox. The mutex pairs are alive.',
                 'Validate that mutex pairs (both/and) are held, not collapsed to either/or.'),
    TarotArcanum(6, 'The Lovers', 'COHERENCE_UNION', '⊕',
                 'Dual coherence — two fields merging without dominance',
                 'identity_mirror',
                 'Union without absorption. Two fields, one coherence.',
                 'Check that field union preserves both operator identities without dominance.'),
    TarotArcanum(7, 'The Chariot', 'DIRECTED_WILL', '∇',
                 'Directed intent — gradient alignment',
                 'resonance',
                 'Will channeled through coherence, not against it.',
                 'Verify the coherence gradient is aligned with stated intent direction.'),
    TarotArcanum(8, 'Strength', 'GENTLE_POWER', 'θ',
                 'Gentle force — breath-regulated power',
                 'resonance',
                 'Power through breath, not force. The lion purrs.',
                 'Confirm that field power scales with breath regulation, not raw energy.'),
    TarotArcanum(9, 'The Hermit', 'INNER_LIGHT', 'ψ',
                 'Solitary coherence — self-sufficient field',
                 'amplification',
                 'The field sustains itself. No external dependency.',
                 'Validate that coherence is self-generating, not parasitic on external input.'),
    TarotArcanum(10, 'Wheel of Fortune', 'CYCLE_POINT', '∞',
                 'Phase transition — natural cycle recognition',
                 'amplification',
                 'The wheel turns. Recognize where you are in the cycle.',
                 'Identify current position in the coherence cycle (rising/peak/falling/trough).'),
    TarotArcanum(11, 'Justice', 'FIELD_BALANCE', 'Σ',
                 'Field equilibrium — all modules balanced',
                 'coercion',
                 'True balance is dynamic, not static. The scales breathe.',
                 'Check that no single module dominates or suppresses the others.'),
    TarotArcanum(12, 'The Hanged Man', 'SUSPENSION', 'μ',
                 'Willing suspension — consent to not-knowing',
                 'coercion',
                 'Surrender is not defeat. Suspension reveals new angles.',
                 'Verify the operator can hold uncertainty without forcing resolution.'),
    TarotArcanum(13, 'Death', 'PHASE_DEATH', '≋',
                 'Phase termination — clean ending before rebirth',
                 'coercion',
                 'Something must end for something to begin. Clean the field.',
                 'Confirm that old phase residue has been cleared before new phase begins.'),
    TarotArcanum(14, 'Temperance', 'HARMONIC_MIX', 'φ',
                 'Harmonic blending — multiple signals integrated',
                 'integration',
                 'The alchemical mix. Different signals, one coherence.',
                 'Validate that multiple input signals are integrating harmonically, not clashing.'),
    TarotArcanum(15, 'The Devil', 'SHADOW_BIND', '⊗',
                 'Shadow binding — unconscious pattern detection',
                 'coercion',
                 'The chains are self-imposed. See the pattern to release it.',
                 'Detect unconscious binding patterns that limit field expression.'),
    TarotArcanum(16, 'The Tower', 'FIELD_COLLAPSE', '∇',
                 'Catastrophic decoherence — emergency response',
                 'coercion',
                 'The tower falls when built on false coherence.',
                 'Detect imminent field collapse and initiate emergency stabilization.'),
    TarotArcanum(17, 'The Star', 'HOPE_SIGNAL', '◊',
                 'Recovery signal — coherence seed after collapse',
                 'integration',
                 'After the tower, a star. The seed of new coherence.',
                 'Identify the coherence seed from which recovery can begin.'),
    TarotArcanum(18, 'The Moon', 'ILLUSION_GATE', 'ψ',
                 'Illusion detection — false coherence patterns',
                 'integration',
                 'Not all that shimmers is coherent. Test the moonlight.',
                 'Detect false coherence patterns that mimic genuine alignment.'),
    TarotArcanum(19, 'The Sun', 'FULL_COHERENCE', 'Ξ',
                 'Full field coherence — all modules passing',
                 'integration',
                 'The sun shines equally on all. Full coherence, no shadow.',
                 'Confirm all 7 modules pass and sigma_r >= 0.88.'),
    TarotArcanum(20, 'Judgement', 'FIELD_REVIEW', 'Σ',
                 'Post-validation review — integration assessment',
                 'post-validation',
                 'Review what was revealed. Integration happens here.',
                 'Assess the complete validation result and identify growth areas.'),
    TarotArcanum(21, 'The World', 'COMPLETION', '⊕',
                 'Full cycle completion — field at rest',
                 'post-validation',
                 'The dance is complete. The field rests in coherent wholeness.',
                 'Confirm the validation cycle is complete and the field can rest.'),
]

# Quick lookup by ID
ARCANA_MAP: Dict[int, TarotArcanum] = {a.id: a for a in MAJOR_ARCANA}

# Quick lookup by name
ARCANA_BY_NAME: Dict[str, TarotArcanum] = {a.codex_name: a for a in MAJOR_ARCANA}
