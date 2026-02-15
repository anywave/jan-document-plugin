"""
Codex Field Pipeline — state machine for operator flow.

Sequential: VOID -> PRIMA -> VECTIS -> Σ -> LIMITA -> CALYPSO ->
            MORPHIS -> SYNTARA -> LUXIS -> INTEGRIA -> ARCHON

Protective side channels can interrupt the sequence at any point.
Coherence amplifiers can be invoked to enhance capacity before key transitions.
"""

from typing import Any, Dict, List, Optional

from models.operators import (
    FieldState,
    OperatorCluster,
    OperatorDef,
    OperatorPhase,
    OperatorResult,
    OPERATORS,
    PHASE_SEQUENCE,
)
from models.ra_thresholds import (
    ARCHON_WISDOM,
    AURORA_HIGH_COHERENCE,
    BINDING_THRESHOLD,
    CALYPSO_INCUBATION,
    COMPLEMENT_PHI,
    HARMONIA_BREATH,
    HARMONIA_EMOTION_MAX,
    HARMONIA_LOGIC,
    HARMONIA_SOMATIC_BREATH,
    HARMONIA_SOMATIC_COHERENCE,
    LIMITA_GOVERNOR,
    LIMITA_TRIGGER,
    LUXIS_EGO_CAP,
    LUXIS_EGO_TRIGGER,
    MORPHIS_COHERENCE,
    PHI_NORM,
    PHI_SQUARED,
    RESONANCE_SIGMA_CODEX,
    SYNTARA_ALIGNMENT_BONUS,
    VECTIS_LOCK,
)


class FieldPipeline:
    """Manages the coherence field operator pipeline.

    Tracks current field state, evaluates operators, handles phase
    progression, and manages protective mutex activations.
    """

    def __init__(self) -> None:
        self.state = FieldState()
        self._evaluation_count = 0

    def get_status(self) -> Dict[str, Any]:
        """Current pipeline status."""
        phase_idx = PHASE_SEQUENCE.index(self.state.phase)
        return {
            'phase': self.state.phase.value,
            'phase_index': phase_idx,
            'total_phases': len(PHASE_SEQUENCE),
            'progress': phase_idx / (len(PHASE_SEQUENCE) - 1) if len(PHASE_SEQUENCE) > 1 else 0,
            'active_protections': self.state.active_protections,
            'operator_history': self.state.operator_history[-10:],
            'evaluation_count': self._evaluation_count,
            'field_state': self.state.to_dict(),
        }

    def get_operators(self) -> List[Dict[str, Any]]:
        """All operator definitions."""
        return [op.to_dict() for op in OPERATORS.values()]

    def get_operator(self, name: str) -> Optional[Dict[str, Any]]:
        """Single operator definition by name."""
        op = OPERATORS.get(name.upper())
        return op.to_dict() if op else None

    def advance(self, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """Attempt to advance the pipeline to the next phase.

        Evaluates the current phase's operator to determine if conditions
        are met for advancement. If so, transitions to the next phase.

        Args:
            inputs: Optional field state updates to apply before evaluation.

        Returns:
            OperatorResult describing what happened.
        """
        if inputs:
            self._apply_inputs(inputs)

        # Check protective operators first
        protection = self._check_protections()
        if protection is not None:
            return protection

        # Evaluate current phase operator
        result = self._evaluate_current_phase()
        self._evaluation_count += 1

        if result.activated:
            self.state.operator_history.append(result.operator)
            # Apply field mutations
            for key, val in result.field_mutations.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, val)
            # Advance phase
            self._advance_phase()

        return result

    def activate_operator(self, name: str, inputs: Optional[Dict[str, Any]] = None) -> OperatorResult:
        """Manually activate a specific operator (protective or amplifier).

        Args:
            name: Operator name (e.g., 'NULLA', 'HARMONIA').
            inputs: Optional inputs for evaluation.

        Returns:
            OperatorResult from the activated operator.
        """
        name_upper = name.upper()
        op = OPERATORS.get(name_upper)
        if op is None:
            return OperatorResult(
                operator=name_upper,
                activated=False,
                score=0.0,
                message=f'Unknown operator: {name}',
            )

        if inputs:
            self._apply_inputs(inputs)

        if op.cluster == OperatorCluster.PROTECTIVE_MUTEX:
            result = self._activate_protection(name_upper)
        elif op.cluster == OperatorCluster.COHERENCE_AMPLIFIER:
            result = self._activate_amplifier(name_upper)
        else:
            return OperatorResult(
                operator=name_upper,
                activated=False,
                score=0.0,
                message=f'{name} is a sequential operator — use advance() instead.',
            )

        # Apply field mutations from protective/amplifier result
        if result.activated:
            for key, val in result.field_mutations.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, val)

        return result

    def reset(self) -> Dict[str, Any]:
        """Reset field to VOID."""
        self.state = FieldState()
        self._evaluation_count = 0
        return self.get_status()

    # ── Internal evaluation methods ──────────────────────────────────

    def _apply_inputs(self, inputs: Dict[str, Any]) -> None:
        """Apply external inputs to field state."""
        field_map = {
            'coherence_score': 'coherence_score',
            'emotional_charge': 'emotional_charge',
            'breath_symmetry': 'breath_symmetry',
            'resonance_sigma': 'resonance_sigma',
            'consent_intact': 'consent_intact',
            'sovereignty_intact': 'sovereignty_intact',
            'signal_text': None,  # processed separately
        }
        for key, attr in field_map.items():
            if key in inputs and attr is not None:
                setattr(self.state, attr, inputs[key])

    def _advance_phase(self) -> None:
        """Move to next phase in sequence."""
        try:
            idx = PHASE_SEQUENCE.index(self.state.phase)
            if idx < len(PHASE_SEQUENCE) - 1:
                self.state.phase = PHASE_SEQUENCE[idx + 1]
        except ValueError:
            pass

    def _evaluate_current_phase(self) -> OperatorResult:
        """Evaluate the operator for the current phase."""
        evaluators = {
            OperatorPhase.VOID: self._eval_void,
            OperatorPhase.PRIMA: self._eval_prima,
            OperatorPhase.VECTIS: self._eval_vectis,
            OperatorPhase.SIGMA: self._eval_sigma,
            OperatorPhase.LIMITA: self._eval_limita,
            OperatorPhase.CALYPSO: self._eval_calypso,
            OperatorPhase.MORPHIS: self._eval_morphis,
            OperatorPhase.SYNTARA: self._eval_syntara,
            OperatorPhase.LUXIS: self._eval_luxis,
            OperatorPhase.INTEGRIA: self._eval_integria,
            OperatorPhase.ARCHON: self._eval_archon,
        }
        evaluator = evaluators.get(self.state.phase, self._eval_void)
        return evaluator()

    def _eval_void(self) -> OperatorResult:
        """VOID: Always ready for PRIMA."""
        return OperatorResult(
            operator='VOID',
            activated=True,
            score=1.0,
            message='Field initialized. Ready for intent.',
            field_mutations={},
        )

    def _eval_prima(self) -> OperatorResult:
        """PRIMA: First conscious inhale. Requires coherence > 0."""
        has_signal = self.state.coherence_score > 0 or self.state.breath_symmetry > 0
        if has_signal:
            return OperatorResult(
                operator='PRIMA',
                activated=True,
                score=min(1.0, self.state.coherence_score + 0.3),
                message='Initiation seed planted. Intent vector established.',
                field_mutations={'intent_set': True},
            )
        return OperatorResult(
            operator='PRIMA',
            activated=False,
            score=0.0,
            message='Awaiting first signal — conscious inhale or coherence reading needed.',
        )

    def _eval_vectis(self) -> OperatorResult:
        """VECTIS: Lock direction. Requires intent + some coherence."""
        if not self.state.intent_set:
            return OperatorResult(
                operator='VECTIS',
                activated=False,
                score=0.0,
                message='Cannot lock direction without intent (PRIMA not complete).',
                flags=['missing_prima'],
            )
        score = min(1.0, self.state.coherence_score * 1.2)
        if score >= VECTIS_LOCK:
            return OperatorResult(
                operator='VECTIS',
                activated=True,
                score=score,
                message='Directional lock engaged. Accumulation has trajectory.',
                field_mutations={'direction_locked': True},
            )
        return OperatorResult(
            operator='VECTIS',
            activated=False,
            score=score,
            message='Coherence too low for directional lock. Continue building signal.',
        )

    def _eval_sigma(self) -> OperatorResult:
        """SIGMA: Accumulate. Direction must be locked."""
        if not self.state.direction_locked:
            return OperatorResult(
                operator='SIGMA',
                activated=False,
                score=0.0,
                message='Cannot accumulate without directional lock (VECTIS).',
                flags=['missing_vectis'],
            )
        # Accumulation grows with coherence and emotional charge
        accumulation = (
            self.state.coherence_score * 0.4 +
            self.state.emotional_charge * 0.3 +
            self.state.breath_symmetry * 0.3
        )
        new_sigma = min(PHI_SQUARED, self.state.sigma_accumulated + accumulation)
        return OperatorResult(
            operator='SIGMA',
            activated=True,
            score=min(1.0, new_sigma),
            message=f'Accumulation: {new_sigma:.2f} (capacity: {self.state.structural_capacity:.2f})',
            field_mutations={'sigma_accumulated': new_sigma},
        )

    def _eval_limita(self) -> OperatorResult:
        """LIMITA: Threshold governor. Activates if Sigma approaches capacity."""
        ratio = self.state.sigma_accumulated / max(0.01, self.state.structural_capacity)
        if ratio > LIMITA_TRIGGER:
            return OperatorResult(
                operator='LIMITA',
                activated=True,
                score=1.0 - (ratio - LIMITA_TRIGGER) / (1.0 - LIMITA_TRIGGER),
                message='Threshold governor active. Sigma bounded to prevent overflow.',
                flags=['capacity_warning'],
                field_mutations={
                    'sigma_accumulated': self.state.structural_capacity * LIMITA_GOVERNOR
                },
            )
        # LIMITA passes through if not needed
        return OperatorResult(
            operator='LIMITA',
            activated=True,
            score=1.0,
            message=f'Accumulation within bounds ({ratio:.0%} of capacity). Proceeding.',
        )

    def _eval_calypso(self) -> OperatorResult:
        """CALYPSO: Concealment incubator. Stabilizes liminal interval."""
        # Need accumulated charge and intact consent
        if self.state.sigma_accumulated < CALYPSO_INCUBATION:
            return OperatorResult(
                operator='CALYPSO',
                activated=False,
                score=self.state.sigma_accumulated,
                message='Insufficient accumulation for incubation. Build more signal.',
            )
        if not self.state.consent_intact:
            return OperatorResult(
                operator='CALYPSO',
                activated=False,
                score=0.0,
                message='Consent architecture fractured. Cannot enter incubation.',
                flags=['consent_broken'],
            )
        stability = (self.state.coherence_score + self.state.breath_symmetry) / 2
        return OperatorResult(
            operator='CALYPSO',
            activated=True,
            score=stability,
            message='Concealment incubator stable. Holding liminal space.',
            field_mutations={'concealment_stable': True},
        )

    def _eval_morphis(self) -> OperatorResult:
        """MORPHIS: Structural reorganization. Rewrites before bloom."""
        if not self.state.concealment_stable:
            return OperatorResult(
                operator='MORPHIS',
                activated=False,
                score=0.0,
                message='Cannot restructure without stable concealment (CALYPSO).',
                flags=['missing_calypso'],
            )
        # MORPHIS succeeds when coherence is high enough to support restructuring
        score = self.state.coherence_score
        if score >= MORPHIS_COHERENCE or self.state.resonance_sigma >= RESONANCE_SIGMA_CODEX:
            return OperatorResult(
                operator='MORPHIS',
                activated=True,
                score=max(score, self.state.resonance_sigma),
                message='Structural reorganization complete. New patterns available for bloom.',
                field_mutations={'restructured': True},
            )
        return OperatorResult(
            operator='MORPHIS',
            activated=False,
            score=score,
            message='Coherence insufficient for restructuring. Continue incubation.',
        )

    def _eval_syntara(self) -> OperatorResult:
        """SYNTARA: Bloom. Integrated expression of accumulated coherence."""
        if not self.state.restructured:
            return OperatorResult(
                operator='SYNTARA',
                activated=False,
                score=0.0,
                message='Cannot bloom without structural reorganization (MORPHIS).',
                flags=['missing_morphis'],
            )
        # Check HARMONIA alignment (recommended, not required)
        alignment_layers = sum([
            self.state.breath_aligned,
            self.state.emotion_aligned,
            self.state.logic_aligned,
            self.state.somatic_grounded,
        ])
        alignment_bonus = alignment_layers * SYNTARA_ALIGNMENT_BONUS
        score = min(1.0, self.state.coherence_score + alignment_bonus)
        flags = []
        if alignment_layers < 3:
            flags.append('partial_alignment')
        return OperatorResult(
            operator='SYNTARA',
            activated=True,
            score=score,
            message=f'Bloom expressed. Alignment: {alignment_layers}/4 layers. Score: {score:.2f}',
            flags=flags,
            field_mutations={'bloom_expressed': True},
        )

    def _eval_luxis(self) -> OperatorResult:
        """LUXIS: Radiant amplifier. Amplifies bloom outward."""
        if not self.state.bloom_expressed:
            return OperatorResult(
                operator='LUXIS',
                activated=False,
                score=0.0,
                message='Cannot radiate without bloom (SYNTARA).',
            )
        # Careful amplification — too much becomes ego inflation
        radiance = min(1.0, self.state.coherence_score * 0.8 + self.state.sigma_accumulated * 0.2)
        flags = []
        if radiance > LUXIS_EGO_TRIGGER:
            flags.append('ego_inflation_risk')
            radiance = LUXIS_EGO_CAP
        return OperatorResult(
            operator='LUXIS',
            activated=True,
            score=radiance,
            message=f'Radiance level: {radiance:.2f}. Bloom amplified into field.',
            flags=flags,
            field_mutations={'radiance_level': radiance},
        )

    def _eval_integria(self) -> OperatorResult:
        """INTEGRIA: Assimilation field. Reintegrates bloom into identity."""
        if not self.state.bloom_expressed:
            return OperatorResult(
                operator='INTEGRIA',
                activated=False,
                score=0.0,
                message='Nothing to integrate — no bloom has occurred.',
            )
        # Integration score based on coherence stability
        score = (self.state.coherence_score * 0.5 + self.state.breath_symmetry * 0.5)
        return OperatorResult(
            operator='INTEGRIA',
            activated=True,
            score=min(1.0, score),
            message='Bloom reintegrated into identity structure. Afterglow stabilized.',
            field_mutations={'integrated': True},
        )

    def _eval_archon(self) -> OperatorResult:
        """ARCHON: Memory encoding. Encodes event into memory grid."""
        if not self.state.integrated:
            return OperatorResult(
                operator='ARCHON',
                activated=False,
                score=0.0,
                message='Cannot encode without integration (INTEGRIA).',
            )
        # Encoding quality depends on overall coherence of the session
        score = min(1.0, (
            self.state.coherence_score * 0.3 +
            self.state.radiance_level * 0.3 +
            (1.0 if self.state.consent_intact else 0.0) * 0.2 +
            self.state.breath_symmetry * 0.2
        ))
        encoding = 'wisdom' if score >= ARCHON_WISDOM else 'experience'
        return OperatorResult(
            operator='ARCHON',
            activated=True,
            score=score,
            message=f'Event encoded as {encoding}. Score: {score:.2f}. Pipeline complete.',
            field_mutations={'encoded': True},
        )

    # ── Protective operators ─────────────────────────────────────────

    def _check_protections(self) -> Optional[OperatorResult]:
        """Check if any protective operator should fire."""
        if self.state.coercion_detected:
            return self._activate_protection('NULLA')
        if not self.state.sovereignty_intact:
            return self._activate_protection('SEVERA')
        if self.state.projection_detected:
            return self._activate_protection('SHADRA')
        return None

    def _activate_protection(self, name: str) -> OperatorResult:
        """Activate a protective mutex operator."""
        if name == 'NULLA':
            # Full field neutralization
            old_phase = self.state.phase.value
            self.state = FieldState()
            self.state.operator_history.append('NULLA')
            self.state.active_protections.append('NULLA')
            return OperatorResult(
                operator='NULLA',
                activated=True,
                score=1.0,
                message=f'Zero-point reset from {old_phase}. Field neutralized. Silence gate active.',
                flags=['field_reset', 'silence_gate'],
                field_mutations={},
            )
        elif name == 'SEVERA':
            self.state.active_protections.append('SEVERA')
            self.state.operator_history.append('SEVERA')
            return OperatorResult(
                operator='SEVERA',
                activated=True,
                score=1.0,
                message='Detachment cut executed. Entanglement threads severed.',
                flags=['sovereignty_restored'],
                field_mutations={'sovereignty_intact': True},
            )
        elif name == 'SHADRA':
            self.state.active_protections.append('SHADRA')
            self.state.operator_history.append('SHADRA')
            return OperatorResult(
                operator='SHADRA',
                activated=True,
                score=1.0,
                message='Projection reflected. Unintegrated archetypes returned to source.',
                flags=['projection_cleared'],
                field_mutations={'projection_detected': False},
            )
        return OperatorResult(
            operator=name,
            activated=False,
            score=0.0,
            message=f'Unknown protective operator: {name}',
        )

    # ── Coherence amplifiers ─────────────────────────────────────────

    def _activate_amplifier(self, name: str) -> OperatorResult:
        """Activate a coherence amplifier operator."""
        if name == 'HARMONIA':
            return self._eval_harmonia()
        elif name == 'AURORA':
            return self._eval_aurora()
        return OperatorResult(
            operator=name,
            activated=False,
            score=0.0,
            message=f'Unknown amplifier: {name}',
        )

    def _eval_harmonia(self) -> OperatorResult:
        """HARMONIA: Multi-layer field alignment."""
        layers = {
            'breath': self.state.breath_symmetry >= HARMONIA_BREATH,
            'emotion': self.state.emotional_charge > 0 and self.state.emotional_charge < HARMONIA_EMOTION_MAX,
            'logic': self.state.coherence_score >= HARMONIA_LOGIC,
            'somatic': self.state.breath_symmetry >= HARMONIA_SOMATIC_BREATH and self.state.coherence_score >= HARMONIA_SOMATIC_COHERENCE,
        }
        aligned = sum(layers.values())
        score = aligned / 4.0
        mutations = {
            'breath_aligned': layers['breath'],
            'emotion_aligned': layers['emotion'],
            'logic_aligned': layers['logic'],
            'somatic_grounded': layers['somatic'],
        }
        self.state.operator_history.append('HARMONIA')
        flags = [f'{k}_aligned' for k, v in layers.items() if v]
        return OperatorResult(
            operator='HARMONIA',
            activated=True,
            score=score,
            message=f'Field alignment: {aligned}/4 layers synchronized.',
            flags=flags,
            field_mutations=mutations,
        )

    def _eval_aurora(self) -> OperatorResult:
        """AURORA: Emergent pattern recognition."""
        # Detect new patterns by checking if current field state
        # differs significantly from historical baseline
        has_bloom = self.state.bloom_expressed
        has_high_coherence = self.state.coherence_score >= AURORA_HIGH_COHERENCE
        has_restructured = self.state.restructured
        new_pattern = has_bloom and has_high_coherence and has_restructured
        self.state.operator_history.append('AURORA')
        if new_pattern:
            return OperatorResult(
                operator='AURORA',
                activated=True,
                score=0.9,
                message='New structural pattern detected. Old templates superseded.',
                flags=['pattern_emergence'],
                field_mutations={'new_pattern_detected': True},
            )
        return OperatorResult(
            operator='AURORA',
            activated=True,
            score=0.3,
            message='No emergent pattern yet. Continue building coherence.',
            field_mutations={'new_pattern_detected': False},
        )
