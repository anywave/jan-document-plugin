"""Integration tests -- full session lifecycle with all components."""
import sys
import os
import pytest
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.session import SessionManager, SessionPhase
from coherence.subjective import SubjectiveTracker
from coherence.scouter import Scouter, DestabilizationClass
from coherence.network import KuramotoNetwork, NetworkNode
from coherence.multiwave_state import MultiWaveCoherenceState


def make_state(ccs: float) -> MultiWaveCoherenceState:
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=np.array([0.5, 0.6, ccs, 0.5, 0.4]),
        band_phases=np.zeros(5),
        signal_coherences={'text': ccs},
        intentionality=0.5,
        breath_entrained=True,
        breath_rate_hz=0.1,
        scalar_coherence=ccs,
        uncertainty=1.0 - ccs,
    )


class TestFullSessionLifecycle:
    def test_session_with_subjective_and_scouter(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        subjective = SubjectiveTracker()
        scouter = Scouter()

        # Start session
        session = mgr.start_session()
        assert session.phase == SessionPhase.DISSOLVE

        # Simulate 5 prompts
        for i in range(5):
            mgr.record_prompt(token_count=250)

        # Feed stable CCS values (triggers DISSOLVE -> PROCESS)
        for _ in range(5):
            state = make_state(0.65)
            scouter.classify(state)
            mgr.record_ccs(0.65)

        assert mgr.active_session.phase == SessionPhase.PROCESS

        # Mid-session subjective prompt
        assert subjective.should_prompt_mid_session(
            prompt_count=5, token_estimate=1250
        )
        entry = subjective.record(session.session_id, 7.0, 'mid_session', 0.65)
        assert entry.divergence < 0.1

        # End session
        ended = mgr.end_session()
        assert ended is not None
        assert ended.prompt_count == 5

    def test_arc_with_bloom_suppression(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        arc = mgr.start_arc(arc_length=5, name="test arc")

        for i in range(5):
            mgr.start_session()
            mgr.record_ccs(0.5 + i * 0.05)

            # Check bloom suppression BEFORE ending the session,
            # since end_session() increments completed_sessions.
            # Bloom is suppressed when completed_sessions < 3.
            if i < 3:
                assert arc.should_suppress_bloom()

            mgr.end_session()

            # After ending session i, completed_sessions = i + 1.
            # Once completed_sessions >= 3 (i >= 2), bloom is no longer suppressed.
            if i >= 2:
                assert not arc.should_suppress_bloom()

        assert arc.arc_status == 'complete'
        assert len(arc.metrics.ccs_trend) == 5

    def test_network_runs_independently(self):
        net = KuramotoNetwork(coupling_strength=1.0)
        net.add_node(NetworkNode('local', phase=0.0, natural_freq=0.1, ccs=0.5))
        net.add_node(NetworkNode('remote', phase=1.0, natural_freq=0.1, ccs=0.3))

        for _ in range(50):
            net.step(0.1)

        assert net.phase_lock_score() > 0.5

    def test_model_confidence_tracks_divergence(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        subjective = SubjectiveTracker()

        # 3 sessions with high divergence
        for i in range(3):
            mgr.start_session()
            mgr.record_ccs(0.8)
            subjective.record(f's{i}', score=2.0, source='end_session', ccs=0.8)
            mgr.end_session()

        assert subjective.has_model_mismatch()
        assert subjective.model_confidence() < 0.5
