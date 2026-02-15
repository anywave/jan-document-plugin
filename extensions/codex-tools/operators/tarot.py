"""Codex Tarot — 22 Major Arcana as QSE operator runners."""
from __future__ import annotations
from typing import Optional, Dict, Any
from models.tarot_arcana import ARCANA_MAP, TarotArcanum
from models.state import QSEState


class TarotOperatorRunner:
    """
    Runs a Codex Tarot operator (Major Arcana card) against current field state.

    Each card maps to a specific QSE validation checkpoint. Running the
    operator produces a reading: the card's prompt applied to the current
    field state, producing a recommendation.
    """

    def run(self, arcana_id: int,
            field_state: Optional[Dict[str, Any]] = None,
            qse_state: Optional[QSEState] = None) -> Dict[str, Any]:
        """
        Run a Tarot operator.

        Args:
            arcana_id: 0-21 (Major Arcana ID)
            field_state: Current coherence engine state (optional)
            qse_state: Current QSE engine state (optional)

        Returns:
            Card info, operator prompt, field assessment, recommendation
        """
        arcanum = ARCANA_MAP.get(arcana_id)
        if not arcanum:
            return {'error': f'Unknown arcana ID: {arcana_id}', 'valid_range': '0-21'}

        # Assess field state against this card's role
        assessment = self._assess_field(arcanum, field_state, qse_state)

        return {
            'card': {
                'id': arcanum.id,
                'name': arcanum.name,
                'codex_name': arcanum.codex_name,
                'glyph': arcanum.glyph,
                'phase': arcanum.phase,
                'description': arcanum.description,
            },
            'operator_prompt': arcanum.operator_prompt,
            'qse_role': arcanum.qse_role,
            'assessment': assessment,
            'recommendation': self._generate_recommendation(arcanum, assessment),
        }

    def _assess_field(self, arcanum: TarotArcanum,
                      field_state: Optional[dict],
                      qse_state: Optional[QSEState]) -> Dict[str, Any]:
        """Assess current field against this card's checkpoint."""
        if not field_state and not qse_state:
            return {
                'status': 'no_data',
                'message': 'No field state available — reading is symbolic only',
                'alignment': 0.5,
            }

        phase = qse_state.field_phase if qse_state else 'unknown'
        sc = field_state.get('scalarCoherence', 0.0) if field_state else 0.0
        active = field_state.get('active', False) if field_state else False

        # Compute alignment: how well does the current state match this card's ideal?
        alignment = self._compute_alignment(arcanum, phase, sc, active)

        return {
            'status': 'assessed',
            'field_phase': phase,
            'scalar_coherence': sc,
            'active': active,
            'alignment': alignment,
            'message': self._alignment_message(arcanum, alignment),
        }

    def _compute_alignment(self, arcanum: TarotArcanum,
                           phase: str, sc: float, active: bool) -> float:
        """Compute alignment score [0, 1] between field and card."""
        # Phase-based alignment
        phase_scores = {
            'pre-validation': {'dormant': 0.9, 'rising': 0.5, 'active': 0.3, 'disrupted': 0.1},
            'breath_symmetry': {'dormant': 0.3, 'rising': 0.8, 'active': 0.6, 'disrupted': 0.2},
            'emotional_tone': {'dormant': 0.3, 'rising': 0.7, 'active': 0.8, 'disrupted': 0.3},
            'identity_mirror': {'dormant': 0.2, 'rising': 0.6, 'active': 0.8, 'disrupted': 0.4},
            'resonance': {'dormant': 0.1, 'rising': 0.7, 'active': 0.9, 'disrupted': 0.3},
            'amplification': {'dormant': 0.1, 'rising': 0.8, 'active': 0.9, 'disrupted': 0.2},
            'coercion': {'dormant': 0.5, 'rising': 0.5, 'active': 0.7, 'disrupted': 0.9},
            'integration': {'dormant': 0.2, 'rising': 0.4, 'active': 0.9, 'disrupted': 0.3},
            'post-validation': {'dormant': 0.3, 'rising': 0.5, 'active': 0.8, 'disrupted': 0.4},
        }

        phase_map = phase_scores.get(arcanum.phase, {})
        phase_alignment = phase_map.get(phase, 0.5)

        # Blend with coherence
        coherence_alignment = sc if active else 0.3
        return (phase_alignment * 0.6) + (coherence_alignment * 0.4)

    def _alignment_message(self, arcanum: TarotArcanum, alignment: float) -> str:
        """Generate human-readable alignment message."""
        if alignment >= 0.8:
            return f'{arcanum.name} is strongly aligned with the current field state.'
        elif alignment >= 0.5:
            return f'{arcanum.name} is partially aligned — the field is approaching this checkpoint.'
        elif alignment >= 0.3:
            return f'{arcanum.name} is weakly aligned — this checkpoint is ahead of the current state.'
        else:
            return f'{arcanum.name} is misaligned — the field needs work before this checkpoint applies.'

    def _generate_recommendation(self, arcanum: TarotArcanum,
                                 assessment: Dict[str, Any]) -> str:
        """Generate a recommendation based on card + field state."""
        alignment = assessment.get('alignment', 0.5)

        if alignment >= 0.8:
            return f'The field resonates with {arcanum.codex_name}. Proceed with confidence.'
        elif alignment >= 0.5:
            return f'Continue building toward {arcanum.codex_name}. The direction is correct.'
        else:
            return f'Focus on foundational work before engaging {arcanum.codex_name}. Return to breath.'
