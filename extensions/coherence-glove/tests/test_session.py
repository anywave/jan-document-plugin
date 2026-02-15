"""Tests for session lifecycle management."""
import sys
import os
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.session import SessionPhase, CoherenceSession, SessionManager


# ── CoherenceSession unit tests ─────────────────────────────────────

class TestCoherenceSession:
    """Tests for CoherenceSession dataclass."""

    def test_create_factory(self):
        session = CoherenceSession.create(metadata={'source': 'test'})
        assert session.phase == SessionPhase.DISSOLVE
        assert session.session_id is not None
        assert session.started_at is not None
        assert session.ended_at is None
        assert session.ccs_history == []
        assert session.peak_ccs == 0.0
        assert session.prompt_count == 0
        assert session.token_estimate == 0
        assert session.metadata == {'source': 'test'}

    def test_record_ccs(self):
        session = CoherenceSession.create()
        session.record_ccs(0.5)
        session.record_ccs(0.8)
        session.record_ccs(0.3)

        assert len(session.ccs_history) == 3
        assert session.peak_ccs == 0.8
        # Values stored correctly
        values = [v for _, v in session.ccs_history]
        assert values == [0.5, 0.8, 0.3]

    def test_record_prompt(self):
        session = CoherenceSession.create()
        session.record_prompt(100)
        session.record_prompt(250)
        assert session.prompt_count == 2
        assert session.token_estimate == 350

    def test_dissolve_to_process_transition(self):
        """DISSOLVE -> PROCESS when 3+ readings within +/-0.05."""
        session = CoherenceSession.create()
        session.record_ccs(0.50)
        assert session.check_phase_transition() is None  # Only 1 reading

        session.record_ccs(0.52)
        assert session.check_phase_transition() is None  # Only 2 readings

        session.record_ccs(0.51)
        result = session.check_phase_transition()
        assert result == SessionPhase.PROCESS
        assert session.phase == SessionPhase.PROCESS

    def test_dissolve_no_transition_unstable(self):
        """No transition when readings are too spread."""
        session = CoherenceSession.create()
        session.record_ccs(0.3)
        session.record_ccs(0.6)
        session.record_ccs(0.9)
        result = session.check_phase_transition()
        assert result is None
        assert session.phase == SessionPhase.DISSOLVE

    def test_process_to_reconstitute_transition(self):
        """PROCESS -> RECONSTITUTE when rising trend AND prompt_count > 5."""
        session = CoherenceSession.create()
        session.force_phase(SessionPhase.PROCESS)

        # Need > 5 prompts
        for i in range(6):
            session.record_prompt(100)

        # Record rising trend
        session.record_ccs(0.5)
        session.record_ccs(0.6)
        session.record_ccs(0.7)

        result = session.check_phase_transition()
        assert result == SessionPhase.RECONSTITUTE
        assert session.phase == SessionPhase.RECONSTITUTE

    def test_process_no_transition_insufficient_prompts(self):
        """No transition to RECONSTITUTE if prompt_count <= 5."""
        session = CoherenceSession.create()
        session.force_phase(SessionPhase.PROCESS)

        session.record_prompt(100)  # Only 1 prompt

        session.record_ccs(0.5)
        session.record_ccs(0.6)
        session.record_ccs(0.7)

        result = session.check_phase_transition()
        assert result is None
        assert session.phase == SessionPhase.PROCESS

    def test_process_no_transition_not_rising(self):
        """No transition to RECONSTITUTE if trend is not rising."""
        session = CoherenceSession.create()
        session.force_phase(SessionPhase.PROCESS)

        for i in range(6):
            session.record_prompt(100)

        session.record_ccs(0.7)
        session.record_ccs(0.6)  # Falling
        session.record_ccs(0.5)

        result = session.check_phase_transition()
        assert result is None
        assert session.phase == SessionPhase.PROCESS

    def test_reconstitute_no_further_transition(self):
        """RECONSTITUTE is terminal -- no further transitions."""
        session = CoherenceSession.create()
        session.force_phase(SessionPhase.RECONSTITUTE)
        session.record_ccs(0.9)
        result = session.check_phase_transition()
        assert result is None

    def test_force_phase(self):
        session = CoherenceSession.create()
        assert session.phase == SessionPhase.DISSOLVE
        session.force_phase(SessionPhase.RECONSTITUTE)
        assert session.phase == SessionPhase.RECONSTITUTE

    def test_end_session(self):
        session = CoherenceSession.create()
        session.record_ccs(0.6)
        session.record_ccs(0.8)
        session.end()
        assert session.ended_at is not None
        assert session.final_ccs == 0.8  # Last reading

    def test_end_session_no_readings(self):
        session = CoherenceSession.create()
        session.end()
        assert session.final_ccs == 0.0

    def test_to_dict_from_dict_roundtrip(self):
        session = CoherenceSession.create(metadata={'test': True})
        session.record_ccs(0.5)
        session.record_ccs(0.7)
        session.record_prompt(200)
        session.force_phase(SessionPhase.PROCESS)

        d = session.to_dict()
        restored = CoherenceSession.from_dict(d)

        assert restored.session_id == session.session_id
        assert restored.phase == session.phase
        assert restored.started_at == session.started_at
        assert restored.peak_ccs == session.peak_ccs
        assert restored.prompt_count == session.prompt_count
        assert restored.token_estimate == session.token_estimate
        assert restored.metadata == session.metadata
        assert len(restored.ccs_history) == len(session.ccs_history)
        for (ts1, v1), (ts2, v2) in zip(restored.ccs_history, session.ccs_history):
            assert ts1 == ts2
            assert v1 == v2


# ── SessionManager tests ────────────────────────────────────────────

class TestSessionManager:
    """Tests for SessionManager."""

    def test_start_session(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        session = mgr.start_session(metadata={'user': 'test'})

        assert session is not None
        assert session.phase == SessionPhase.DISSOLVE
        assert mgr.active_session is session
        assert (tmp_path / "sessions").is_dir()

    def test_end_session_persists(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        session = mgr.start_session()
        session.record_ccs(0.6)
        sid = session.session_id

        ended = mgr.end_session()
        assert ended is not None
        assert ended.ended_at is not None
        assert ended.final_ccs == 0.6
        assert mgr.active_session is None

        # Verify JSON file was written
        json_file = tmp_path / "sessions" / f"session_{sid}.json"
        assert json_file.exists()

        with open(json_file, 'r') as f:
            data = json.load(f)
        assert data['session_id'] == sid
        assert data['final_ccs'] == 0.6

    def test_start_new_ends_previous(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        first = mgr.start_session(metadata={'n': 1})
        first_id = first.session_id

        second = mgr.start_session(metadata={'n': 2})
        assert second.session_id != first_id
        assert mgr.active_session is second

        # First session should have been persisted
        json_file = tmp_path / "sessions" / f"session_{first_id}.json"
        assert json_file.exists()

    def test_record_ccs_triggers_phase_transition(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        mgr.start_session()

        # First two readings: no transition
        assert mgr.record_ccs(0.50) is None
        assert mgr.record_ccs(0.52) is None

        # Third stable reading triggers DISSOLVE -> PROCESS
        result = mgr.record_ccs(0.51)
        assert result == SessionPhase.PROCESS
        assert mgr.active_session.phase == SessionPhase.PROCESS

    def test_get_status_no_session(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        status = mgr.get_status()
        assert status['active'] is False
        assert status['session_id'] is None
        assert status['phase'] is None

    def test_get_status_active_session(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        session = mgr.start_session()
        session.record_ccs(0.7)

        status = mgr.get_status()
        assert status['active'] is True
        assert status['session_id'] == session.session_id
        assert status['phase'] == 'dissolve'
        assert status['ccs_readings'] == 1

    def test_load_recent_sessions(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))

        # Create and end 3 sessions
        for i in range(3):
            s = mgr.start_session(metadata={'index': i})
            s.record_ccs(0.1 * (i + 1))

        # End the last one explicitly
        mgr.end_session()

        # All 3 should be persisted (first 2 ended by start_session, 3rd by end_session)
        loaded = mgr.load_recent_sessions(count=10)
        assert len(loaded) == 3

        # Most recent first
        assert loaded[0].metadata.get('index') == 2

    def test_load_recent_sessions_limited(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))

        for i in range(5):
            s = mgr.start_session(metadata={'index': i})
            s.record_ccs(0.5)

        mgr.end_session()

        loaded = mgr.load_recent_sessions(count=2)
        assert len(loaded) == 2

    def test_record_prompt_delegates(self, tmp_path):
        mgr = SessionManager(str(tmp_path / "sessions"))
        mgr.start_session()

        mgr.record_prompt(150)
        mgr.record_prompt(300)

        assert mgr.active_session.prompt_count == 2
        assert mgr.active_session.token_estimate == 450

    def test_record_prompt_no_session(self, tmp_path):
        """record_prompt is a no-op when no session active."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        mgr.record_prompt(100)  # Should not raise

    def test_record_ccs_no_session(self, tmp_path):
        """record_ccs returns None when no session active."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        assert mgr.record_ccs(0.5) is None

    def test_end_session_no_session(self, tmp_path):
        """end_session returns None when no session active."""
        mgr = SessionManager(str(tmp_path / "sessions"))
        assert mgr.end_session() is None
