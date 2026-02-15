"""Tests for subjective coherence score tracking."""
import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.subjective import SubjectiveEntry, SubjectiveTracker
from datetime import datetime


# -- SubjectiveEntry tests ---------------------------------------------------

class TestSubjectiveEntry:

    def test_create_entry(self):
        """Verify divergence = abs(7/10 - 0.65) ~= 0.05."""
        entry = SubjectiveEntry(
            timestamp=datetime.now(),
            session_id="sess-001",
            score=7.0,
            source="end_session",
            ccs_at_time=0.65,
        )
        assert entry.session_id == "sess-001"
        assert entry.score == 7.0
        assert entry.source == "end_session"
        assert entry.ccs_at_time == 0.65
        assert abs(entry.divergence - 0.05) < 1e-9

    def test_divergence_calculation(self):
        """score=3, ccs=0.8 -> divergence = abs(0.3 - 0.8) = 0.5."""
        entry = SubjectiveEntry(
            timestamp=datetime.now(),
            session_id="sess-002",
            score=3.0,
            source="mid_session",
            ccs_at_time=0.8,
        )
        assert abs(entry.divergence - 0.5) < 1e-9

    def test_to_dict(self):
        ts = datetime(2026, 2, 14, 12, 0, 0)
        entry = SubjectiveEntry(
            timestamp=ts,
            session_id="sess-003",
            score=5.0,
            source="end_session",
            ccs_at_time=0.5,
        )
        d = entry.to_dict()
        assert d["timestamp"] == ts.isoformat()
        assert d["session_id"] == "sess-003"
        assert d["score"] == 5.0
        assert d["source"] == "end_session"
        assert d["ccs_at_time"] == 0.5
        assert abs(d["divergence"] - 0.0) < 1e-9


# -- SubjectiveTracker tests -------------------------------------------------

class TestSubjectiveTracker:

    def test_record_score(self):
        """record() stores an entry and clamps out-of-range scores."""
        tracker = SubjectiveTracker()
        entry = tracker.record("sess-A", 7.5, "end_session", 0.7)
        assert entry.score == 7.5
        assert entry.session_id == "sess-A"

        # Score clamped to 0-10
        low = tracker.record("sess-A", -2.0, "mid_session", 0.5)
        assert low.score == 0.0
        high = tracker.record("sess-A", 15.0, "end_session", 0.9)
        assert high.score == 10.0

    def test_model_mismatch_detection(self):
        """3 sessions with divergence > 0.3 triggers mismatch."""
        tracker = SubjectiveTracker(
            mismatch_threshold=0.3,
            mismatch_min_sessions=3,
        )
        # score=1, ccs=0.8 -> divergence = abs(0.1 - 0.8) = 0.7
        tracker.record("s1", 1.0, "end_session", 0.8)
        assert not tracker.has_model_mismatch()  # only 1

        tracker.record("s2", 1.0, "end_session", 0.8)
        assert not tracker.has_model_mismatch()  # only 2

        tracker.record("s3", 1.0, "end_session", 0.8)
        assert tracker.has_model_mismatch()  # 3 — triggered

    def test_no_mismatch_when_aligned(self):
        """When subjective and CCS agree, no mismatch."""
        tracker = SubjectiveTracker(
            mismatch_threshold=0.3,
            mismatch_min_sessions=3,
        )
        # score=7, ccs=0.7 -> divergence = 0.0
        for i in range(5):
            tracker.record(f"s{i}", 7.0, "end_session", 0.7)
        assert not tracker.has_model_mismatch()

    def test_average_divergence(self):
        """avg_divergence averages across all entries."""
        tracker = SubjectiveTracker()
        # Entry 1: score=7, ccs=0.65 -> div = 0.05
        tracker.record("s1", 7.0, "end_session", 0.65)
        # Entry 2: score=3, ccs=0.8 -> div = 0.5
        tracker.record("s2", 3.0, "end_session", 0.8)
        # avg = (0.05 + 0.5) / 2 = 0.275
        assert abs(tracker.avg_divergence() - 0.275) < 1e-9

    def test_model_confidence(self):
        """model_confidence = max(0, 1 - avg_divergence)."""
        tracker = SubjectiveTracker()
        # No entries -> avg_divergence = 0 -> confidence = 1.0
        assert tracker.model_confidence() == 1.0

        # score=3, ccs=0.8 -> div=0.5 -> confidence = 0.5
        tracker.record("s1", 3.0, "end_session", 0.8)
        assert abs(tracker.model_confidence() - 0.5) < 1e-9

    def test_should_prompt_mid_session(self):
        """Only True when both thresholds met and not yet prompted."""
        tracker = SubjectiveTracker(
            mid_session_min_prompts=3,
            mid_session_min_tokens=1000,
        )
        # Below both thresholds
        assert not tracker.should_prompt_mid_session(1, 500)
        # Prompts met, tokens not
        assert not tracker.should_prompt_mid_session(3, 500)
        # Tokens met, prompts not
        assert not tracker.should_prompt_mid_session(2, 1500)
        # Both met
        assert tracker.should_prompt_mid_session(3, 1000)
        assert tracker.should_prompt_mid_session(5, 2000)

    def test_no_duplicate_mid_session_prompt(self):
        """Once a mid-session rating is recorded, don't prompt again."""
        tracker = SubjectiveTracker(
            mid_session_min_prompts=3,
            mid_session_min_tokens=1000,
        )
        assert tracker.should_prompt_mid_session(5, 2000)

        # Simulate recording a mid-session score
        tracker.record("s1", 6.0, "mid_session", 0.6)

        # Now it should NOT prompt again
        assert not tracker.should_prompt_mid_session(10, 5000)

        # After reset_session, it should prompt again
        tracker.reset_session()
        assert tracker.should_prompt_mid_session(5, 2000)
