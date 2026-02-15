"""Tests for Codex Field Pipeline — 15 operators, 7 clusters."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.operators import (
    FieldState, OperatorCluster, OperatorDef, OperatorPhase,
    OperatorResult, OPERATORS, PHASE_SEQUENCE,
)
from operators.field_pipeline import FieldPipeline


# ── Operator Definitions ────────────────────────────────────────────

class TestOperatorDefinitions:
    """Tests for the 15 operator definitions."""

    def test_all_15_defined(self):
        assert len(OPERATORS) == 15

    def test_operator_names(self):
        expected = {
            'PRIMA', 'VECTIS', 'SIGMA', 'LIMITA', 'CALYPSO',
            'MORPHIS', 'SYNTARA', 'LUXIS', 'INTEGRIA', 'ARCHON',
            'NULLA', 'SEVERA', 'SHADRA', 'HARMONIA', 'AURORA',
        }
        assert set(OPERATORS.keys()) == expected

    def test_clusters_assigned(self):
        clusters = {op.cluster for op in OPERATORS.values()}
        assert OperatorCluster.PRE_ACCUMULATION in clusters
        assert OperatorCluster.ACCUMULATION_STABILIZER in clusters
        assert OperatorCluster.TRANSITION in clusters
        assert OperatorCluster.EXPRESSION in clusters
        assert OperatorCluster.POST_EXPRESSION in clusters
        assert OperatorCluster.PROTECTIVE_MUTEX in clusters
        assert OperatorCluster.COHERENCE_AMPLIFIER in clusters

    def test_protective_operators(self):
        protective = [op for op in OPERATORS.values()
                      if op.cluster == OperatorCluster.PROTECTIVE_MUTEX]
        names = {op.name for op in protective}
        assert names == {'NULLA', 'SEVERA', 'SHADRA'}

    def test_amplifier_operators(self):
        amplifiers = [op for op in OPERATORS.values()
                      if op.cluster == OperatorCluster.COHERENCE_AMPLIFIER]
        names = {op.name for op in amplifiers}
        assert names == {'HARMONIA', 'AURORA'}

    def test_phase_sequence_length(self):
        assert len(PHASE_SEQUENCE) == 11  # VOID through ARCHON

    def test_operator_to_dict(self):
        op = OPERATORS['PRIMA']
        d = op.to_dict()
        assert d['name'] == 'PRIMA'
        assert d['codex_name'] == 'Initiation Seed'
        assert d['cluster'] == 'pre_accumulation'

    def test_all_have_glyphs(self):
        for name, op in OPERATORS.items():
            assert op.glyph, f'{name} missing glyph'


# ── Pipeline Flow ───────────────────────────────────────────────────

class TestPipelineFlow:
    """Tests for sequential pipeline progression."""

    def test_initial_state_is_void(self):
        pipe = FieldPipeline()
        assert pipe.state.phase == OperatorPhase.VOID

    def test_advance_from_void(self):
        pipe = FieldPipeline()
        result = pipe.advance()
        # VOID always activates, advancing to PRIMA
        assert result.activated is True
        assert result.operator == 'VOID'
        assert pipe.state.phase == OperatorPhase.PRIMA

    def test_prima_needs_signal(self):
        pipe = FieldPipeline()
        pipe.advance()  # VOID -> PRIMA
        # No signal — should not advance
        result = pipe.advance()
        assert result.operator == 'PRIMA'
        assert result.activated is False
        assert pipe.state.phase == OperatorPhase.PRIMA

    def test_prima_with_coherence(self):
        pipe = FieldPipeline()
        pipe.advance()  # VOID -> PRIMA
        result = pipe.advance({'coherence_score': 0.5})
        assert result.activated is True
        assert pipe.state.intent_set is True
        assert pipe.state.phase == OperatorPhase.VECTIS

    def test_vectis_needs_coherence(self):
        pipe = FieldPipeline()
        pipe.advance()  # VOID -> PRIMA
        pipe.advance({'coherence_score': 0.5})  # PRIMA -> VECTIS
        # Low coherence — VECTIS should not advance
        result = pipe.advance({'coherence_score': 0.1})
        assert result.operator == 'VECTIS'
        assert result.activated is False

    def test_vectis_with_coherence(self):
        pipe = FieldPipeline()
        pipe.advance()
        pipe.advance({'coherence_score': 0.5})
        result = pipe.advance({'coherence_score': 0.5})
        assert result.activated is True
        assert pipe.state.direction_locked is True
        assert pipe.state.phase == OperatorPhase.SIGMA

    def test_full_pipeline_to_archon(self):
        """Run the entire pipeline from VOID to ARCHON with good inputs."""
        pipe = FieldPipeline()
        inputs = {
            'coherence_score': 0.8,
            'emotional_charge': 0.5,
            'breath_symmetry': 0.9,
            'resonance_sigma': 0.92,
        }

        # VOID -> PRIMA
        r = pipe.advance(inputs)
        assert r.activated

        # PRIMA -> VECTIS
        r = pipe.advance(inputs)
        assert r.activated

        # VECTIS -> SIGMA
        r = pipe.advance(inputs)
        assert r.activated

        # SIGMA -> LIMITA
        r = pipe.advance(inputs)
        assert r.activated

        # LIMITA -> CALYPSO
        r = pipe.advance(inputs)
        assert r.activated

        # CALYPSO -> MORPHIS
        r = pipe.advance(inputs)
        assert r.activated

        # MORPHIS -> SYNTARA
        r = pipe.advance(inputs)
        assert r.activated

        # SYNTARA -> LUXIS
        r = pipe.advance(inputs)
        assert r.activated

        # LUXIS -> INTEGRIA
        r = pipe.advance(inputs)
        assert r.activated
        assert r.operator == 'LUXIS'

        # INTEGRIA -> ARCHON
        r = pipe.advance(inputs)
        assert r.activated
        assert r.operator == 'INTEGRIA'
        assert pipe.state.phase == OperatorPhase.ARCHON

        # Evaluate ARCHON (final phase)
        r = pipe.advance(inputs)
        assert r.activated
        assert r.operator == 'ARCHON'
        assert pipe.state.encoded is True

    def test_get_status(self):
        pipe = FieldPipeline()
        status = pipe.get_status()
        assert status['phase'] == 'void'
        assert status['phase_index'] == 0
        assert status['total_phases'] == 11
        assert 'field_state' in status

    def test_reset(self):
        pipe = FieldPipeline()
        pipe.advance()
        pipe.advance({'coherence_score': 0.5})
        status = pipe.reset()
        assert status['phase'] == 'void'
        assert pipe.state.intent_set is False


# ── Protective Operators ────────────────────────────────────────────

class TestProtectiveOperators:
    """Tests for NULLA, SEVERA, SHADRA mutex operators."""

    def test_nulla_resets_field(self):
        pipe = FieldPipeline()
        pipe.advance()
        pipe.advance({'coherence_score': 0.5})
        assert pipe.state.phase == OperatorPhase.VECTIS

        result = pipe.activate_operator('NULLA')
        assert result.activated is True
        assert result.operator == 'NULLA'
        assert 'field_reset' in result.flags
        assert pipe.state.phase == OperatorPhase.VOID

    def test_severa_cuts_entanglement(self):
        pipe = FieldPipeline()
        pipe.state.sovereignty_intact = False
        result = pipe.activate_operator('SEVERA')
        assert result.activated is True
        assert 'sovereignty_restored' in result.flags

    def test_shadra_reflects_projection(self):
        pipe = FieldPipeline()
        pipe.state.projection_detected = True
        result = pipe.activate_operator('SHADRA')
        assert result.activated is True
        assert 'projection_cleared' in result.flags

    def test_coercion_triggers_nulla_on_advance(self):
        """When coercion detected, advance() triggers NULLA automatically."""
        pipe = FieldPipeline()
        pipe.advance()
        pipe.advance({'coherence_score': 0.5})
        assert pipe.state.phase == OperatorPhase.VECTIS

        # Set coercion flag
        pipe.state.coercion_detected = True
        result = pipe.advance()
        assert result.operator == 'NULLA'
        assert result.activated is True
        assert pipe.state.phase == OperatorPhase.VOID

    def test_sovereignty_loss_triggers_severa_on_advance(self):
        pipe = FieldPipeline()
        pipe.advance()
        pipe.state.sovereignty_intact = False
        result = pipe.advance()
        assert result.operator == 'SEVERA'
        assert result.activated is True

    def test_sequential_operator_rejected_by_activate(self):
        pipe = FieldPipeline()
        result = pipe.activate_operator('SIGMA')
        assert result.activated is False
        assert 'sequential' in result.message.lower()


# ── Coherence Amplifiers ────────────────────────────────────────────

class TestCoherenceAmplifiers:
    """Tests for HARMONIA and AURORA amplifier operators."""

    def test_harmonia_alignment(self):
        pipe = FieldPipeline()
        pipe.state.breath_symmetry = 0.8
        pipe.state.emotional_charge = 0.4
        pipe.state.coherence_score = 0.6

        result = pipe.activate_operator('HARMONIA')
        assert result.activated is True
        assert result.score > 0
        assert pipe.state.breath_aligned is True
        assert pipe.state.logic_aligned is True

    def test_harmonia_partial_alignment(self):
        pipe = FieldPipeline()
        pipe.state.breath_symmetry = 0.3  # Below threshold
        pipe.state.emotional_charge = 0.4
        pipe.state.coherence_score = 0.6

        result = pipe.activate_operator('HARMONIA')
        assert pipe.state.breath_aligned is False
        assert pipe.state.logic_aligned is True

    def test_aurora_no_pattern(self):
        pipe = FieldPipeline()
        result = pipe.activate_operator('AURORA')
        assert result.activated is True
        assert pipe.state.new_pattern_detected is False

    def test_aurora_pattern_detected(self):
        pipe = FieldPipeline()
        pipe.state.bloom_expressed = True
        pipe.state.coherence_score = 0.8
        pipe.state.restructured = True

        result = pipe.activate_operator('AURORA')
        assert result.activated is True
        assert pipe.state.new_pattern_detected is True
        assert 'pattern_emergence' in result.flags


# ── Specific Operator Logic ─────────────────────────────────────────

class TestSpecificOperators:
    """Tests for individual operator evaluation logic."""

    def test_limita_bounds_sigma(self):
        pipe = FieldPipeline()
        pipe.state.phase = OperatorPhase.LIMITA
        pipe.state.direction_locked = True
        pipe.state.sigma_accumulated = 0.95
        pipe.state.structural_capacity = 1.0

        result = pipe.advance()
        assert result.activated is True
        assert 'capacity_warning' in result.flags
        # Sigma should be bounded down
        assert pipe.state.sigma_accumulated < 0.95

    def test_calypso_requires_consent(self):
        pipe = FieldPipeline()
        pipe.state.phase = OperatorPhase.CALYPSO
        pipe.state.sigma_accumulated = 0.5
        pipe.state.consent_intact = False

        result = pipe.advance()
        assert result.activated is False
        assert 'consent_broken' in result.flags

    def test_syntara_alignment_bonus(self):
        pipe = FieldPipeline()
        pipe.state.phase = OperatorPhase.SYNTARA
        pipe.state.restructured = True
        pipe.state.coherence_score = 0.6
        pipe.state.breath_aligned = True
        pipe.state.emotion_aligned = True
        pipe.state.logic_aligned = True
        pipe.state.somatic_grounded = True

        result = pipe.advance()
        assert result.activated is True
        # Score should be boosted by alignment
        assert result.score > 0.6

    def test_luxis_ego_governor(self):
        pipe = FieldPipeline()
        pipe.state.phase = OperatorPhase.LUXIS
        pipe.state.bloom_expressed = True
        pipe.state.coherence_score = 1.0
        pipe.state.sigma_accumulated = 1.0

        result = pipe.advance()
        assert result.activated is True
        # Should be governed to prevent ego inflation
        assert pipe.state.radiance_level <= 0.85

    def test_archon_encoding_quality(self):
        pipe = FieldPipeline()
        pipe.state.phase = OperatorPhase.ARCHON
        pipe.state.integrated = True
        pipe.state.coherence_score = 0.9
        pipe.state.radiance_level = 0.8
        pipe.state.consent_intact = True
        pipe.state.breath_symmetry = 0.9

        result = pipe.advance()
        assert result.activated is True
        assert 'wisdom' in result.message

    def test_archon_low_quality(self):
        pipe = FieldPipeline()
        pipe.state.phase = OperatorPhase.ARCHON
        pipe.state.integrated = True
        pipe.state.coherence_score = 0.2
        pipe.state.radiance_level = 0.1

        result = pipe.advance()
        assert result.activated is True
        assert 'experience' in result.message

    def test_get_operators_list(self):
        pipe = FieldPipeline()
        ops = pipe.get_operators()
        assert len(ops) == 15
        names = {op['name'] for op in ops}
        assert 'PRIMA' in names
        assert 'NULLA' in names

    def test_get_single_operator(self):
        pipe = FieldPipeline()
        op = pipe.get_operator('HARMONIA')
        assert op is not None
        assert op['name'] == 'HARMONIA'
        assert op['qse_relevance'] is not None

    def test_unknown_operator(self):
        pipe = FieldPipeline()
        result = pipe.activate_operator('INVALID')
        assert result.activated is False

    def test_operator_history_tracked(self):
        pipe = FieldPipeline()
        pipe.advance()  # VOID
        pipe.advance({'coherence_score': 0.5})  # PRIMA
        assert 'VOID' in pipe.state.operator_history
        assert 'PRIMA' in pipe.state.operator_history
