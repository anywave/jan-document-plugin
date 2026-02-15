"""Tests for ArcSession multi-session arc tracking."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.session import (
    ArcMetrics,
    ArcSession,
    CoherenceSession,
    SessionManager,
    SessionPhase,
)


# ── Helper ───────────────────────────────────────────────────────────

def _make_ended_session(
    final_ccs: float = 0.5,
    metadata: dict = None,
) -> CoherenceSession:
    """Create an ended CoherenceSession with a known final_ccs."""
    session = CoherenceSession.create(metadata=metadata or {})
    session.record_ccs(final_ccs)
    session.end()
    return session


# ── ArcSession unit tests ───────────────────────────────────────────

class TestArcSession:
    """Tests for ArcMetrics and ArcSession dataclasses."""

    def test_create_arc(self):
        """ArcSession.create produces a valid active arc."""
        arc = ArcSession.create(arc_length=5, name="test arc")

        assert arc.arc_id is not None
        assert arc.arc_name == "test arc"
        assert arc.arc_length == 5
        assert arc.completed_sessions == 0
        assert arc.session_ids == []
        assert arc.arc_status == 'active'
        assert arc.created_at is not None
        assert arc.updated_at is not None
        assert isinstance(arc.metrics, ArcMetrics)
        assert arc.metrics.avg_ccs == 0.0
        assert arc.metrics.ccs_trend == []
        assert arc.metrics.model_mismatch_count == 0

    def test_add_session(self):
        """add_session updates completed_sessions and ccs_trend."""
        arc = ArcSession.create(arc_length=5)
        s1 = _make_ended_session(final_ccs=0.4)
        s2 = _make_ended_session(final_ccs=0.6)

        arc.add_session(s1)
        assert arc.completed_sessions == 1
        assert arc.metrics.ccs_trend == [0.4]
        assert arc.metrics.avg_ccs == pytest.approx(0.4)
        assert s1.session_id in arc.session_ids

        arc.add_session(s2)
        assert arc.completed_sessions == 2
        assert arc.metrics.ccs_trend == [0.4, 0.6]
        assert arc.metrics.avg_ccs == pytest.approx(0.5)
        assert s2.session_id in arc.session_ids

    def test_auto_complete(self):
        """Arc auto-completes when completed_sessions >= arc_length."""
        arc = ArcSession.create(arc_length=3)
        assert arc.arc_status == 'active'

        for i in range(3):
            arc.add_session(_make_ended_session(final_ccs=0.3 + 0.1 * i))

        assert arc.completed_sessions == 3
        assert arc.arc_status == 'complete'

    def test_bloom_suppressed_before_session_3(self):
        """should_suppress_bloom is True for first 3 sessions."""
        arc = ArcSession.create(arc_length=10)

        # 0 sessions -- suppress
        assert arc.should_suppress_bloom() is True

        arc.add_session(_make_ended_session(0.3))
        assert arc.should_suppress_bloom() is True  # 1 session

        arc.add_session(_make_ended_session(0.4))
        assert arc.should_suppress_bloom() is True  # 2 sessions

        arc.add_session(_make_ended_session(0.5))
        assert arc.should_suppress_bloom() is False  # 3 sessions -- no longer suppress

    def test_progressive_ccs_threshold(self):
        """ccs_threshold_for_session increases by 0.05 per index."""
        arc = ArcSession.create(arc_length=10)

        assert arc.ccs_threshold_for_session(0) == pytest.approx(0.30)
        assert arc.ccs_threshold_for_session(1) == pytest.approx(0.35)
        assert arc.ccs_threshold_for_session(2) == pytest.approx(0.40)
        assert arc.ccs_threshold_for_session(5) == pytest.approx(0.55)
        assert arc.ccs_threshold_for_session(10) == pytest.approx(0.80)

    def test_to_dict_roundtrip(self):
        """to_dict / from_dict roundtrip preserves all fields."""
        arc = ArcSession.create(arc_length=4, name="roundtrip test")
        arc.add_session(_make_ended_session(
            final_ccs=0.6,
            metadata={'subjective_score': 0.7, 'entropy': 0.3, 'rtc': 0.5},
        ))
        arc.add_session(_make_ended_session(
            final_ccs=0.8,
            metadata={'model_confidence': 0.1},  # big mismatch with 0.8
        ))

        d = arc.to_dict()
        restored = ArcSession.from_dict(d)

        assert restored.arc_id == arc.arc_id
        assert restored.arc_name == arc.arc_name
        assert restored.arc_length == arc.arc_length
        assert restored.completed_sessions == arc.completed_sessions
        assert restored.session_ids == arc.session_ids
        assert restored.arc_status == arc.arc_status
        assert restored.created_at == arc.created_at
        assert restored.updated_at == arc.updated_at

        # Metrics roundtrip
        assert restored.metrics.avg_ccs == pytest.approx(arc.metrics.avg_ccs)
        assert restored.metrics.ccs_trend == arc.metrics.ccs_trend
        assert restored.metrics.entropy_trend == arc.metrics.entropy_trend
        assert restored.metrics.rtc_trend == arc.metrics.rtc_trend
        assert restored.metrics.subjective_trend == arc.metrics.subjective_trend
        assert restored.metrics.model_mismatch_count == arc.metrics.model_mismatch_count


# ── SessionManager arc integration tests ─────────────────────────────

class TestSessionManagerArc:
    """Tests for arc tracking in SessionManager."""

    def test_start_and_get_arc(self, tmp_path):
        """start_arc creates an arc; get_arc_status reports it."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        arc = mgr.start_arc(arc_length=5, name="integration arc")

        assert arc.arc_status == 'active'
        assert arc.arc_length == 5

        status = mgr.get_arc_status()
        assert status['active'] is True
        assert status['arc_id'] == arc.arc_id
        assert status['arc_name'] == "integration arc"
        assert status['completed_sessions'] == 0
        assert status['suppress_bloom'] is True

    def test_session_auto_attaches_to_arc(self, tmp_path):
        """Ending a session auto-attaches it to the active arc."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        arc = mgr.start_arc(arc_length=5)

        # Run a session
        session = mgr.start_session()
        session.record_ccs(0.65)
        ended = mgr.end_session()

        assert mgr.active_arc is not None
        assert mgr.active_arc.completed_sessions == 1
        assert ended.session_id in mgr.active_arc.session_ids
        assert mgr.active_arc.metrics.ccs_trend == [0.65]

    def test_arc_persists(self, tmp_path):
        """Arc data is persisted to arcs.json."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        arc = mgr.start_arc(arc_length=3, name="persist test")

        # Add a session so there's meaningful data
        session = mgr.start_session()
        session.record_ccs(0.7)
        mgr.end_session()

        # Verify arcs.json exists with correct data
        arcs_file = tmp_path / "sessions" / "arcs.json"
        assert arcs_file.exists()

        with open(arcs_file, 'r') as f:
            arcs_data = json.load(f)

        assert len(arcs_data) >= 1
        arc_dict = arcs_data[-1]
        assert arc_dict['arc_id'] == arc.arc_id
        assert arc_dict['arc_name'] == "persist test"
        assert arc_dict['completed_sessions'] == 1
        assert arc_dict['metrics']['ccs_trend'] == [0.7]

    def test_start_arc_interrupts_existing(self, tmp_path):
        """Starting a new arc interrupts the previous active arc."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        first = mgr.start_arc(arc_length=5, name="first")
        second = mgr.start_arc(arc_length=3, name="second")

        # First arc should be interrupted
        assert first.arc_status == 'interrupted'
        # Second arc is now active
        assert mgr.active_arc.arc_id == second.arc_id
        assert mgr.active_arc.arc_status == 'active'

    def test_get_arc_status_no_arc(self, tmp_path):
        """get_arc_status returns minimal dict when no arc active."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        status = mgr.get_arc_status()
        assert status['active'] is False
        assert status['arc_id'] is None

    def test_end_arc(self, tmp_path):
        """end_arc manually closes the arc."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        arc = mgr.start_arc(arc_length=10, name="manual close")
        ended = mgr.end_arc()

        assert ended is not None
        assert ended.arc_status == 'complete'
        assert mgr.active_arc is None
