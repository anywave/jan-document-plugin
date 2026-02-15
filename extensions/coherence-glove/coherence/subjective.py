"""
Subjective Coherence Score tracking.

Captures the user's self-reported coherence rating alongside the
computed CCS, tracks divergence between subjective and objective
measures, and detects model mismatch when the two consistently
disagree.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class SubjectiveEntry:
    """A single subjective coherence rating.

    Attributes:
        timestamp: When the rating was recorded.
        session_id: Which session this rating belongs to.
        score: User-reported coherence score (0-10 scale).
        source: When the rating was collected
            ("mid_session" or "end_session").
        ccs_at_time: The computed CCS (0-1 scale) at rating time.
    """
    timestamp: datetime
    session_id: str
    score: float
    source: str  # "mid_session" | "end_session"
    ccs_at_time: float

    @property
    def divergence(self) -> float:
        """Absolute difference between normalized score and CCS.

        Score is divided by 10 to normalize to the 0-1 CCS range,
        then we take the absolute difference.
        """
        return abs(self.score / 10.0 - self.ccs_at_time)

    def to_dict(self) -> Dict:
        """Serialize to a plain dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "session_id": self.session_id,
            "score": self.score,
            "source": self.source,
            "ccs_at_time": self.ccs_at_time,
            "divergence": self.divergence,
        }


class SubjectiveTracker:
    """Tracks subjective coherence ratings across sessions.

    Monitors the gap between user-reported coherence and computed CCS.
    When divergence is consistently high, flags a model mismatch --
    meaning the coherence model may not reflect the user's actual
    experience.

    Args:
        mismatch_threshold: Divergence above this triggers mismatch
            concern (default 0.3).
        mismatch_min_sessions: How many consecutive end_session entries
            must exceed the threshold before flagging mismatch
            (default 3).
        mid_session_min_prompts: Minimum prompts before mid-session
            rating is offered (default 3).
        mid_session_min_tokens: Minimum estimated tokens before
            mid-session rating is offered (default 1000).
    """

    def __init__(
        self,
        mismatch_threshold: float = 0.3,
        mismatch_min_sessions: int = 3,
        mid_session_min_prompts: int = 3,
        mid_session_min_tokens: int = 1000,
    ):
        self.mismatch_threshold = mismatch_threshold
        self.mismatch_min_sessions = mismatch_min_sessions
        self.mid_session_min_prompts = mid_session_min_prompts
        self.mid_session_min_tokens = mid_session_min_tokens

        self._entries: List[SubjectiveEntry] = []
        self._mid_session_prompted: bool = False

    def record(
        self,
        session_id: str,
        score: float,
        source: str,
        ccs: float,
    ) -> SubjectiveEntry:
        """Record a subjective coherence rating.

        Args:
            session_id: Current session identifier.
            score: User-reported score (clamped to 0-10).
            source: "mid_session" or "end_session".
            ccs: Current computed CCS value (0-1).

        Returns:
            The created SubjectiveEntry.
        """
        score = max(0.0, min(10.0, float(score)))

        entry = SubjectiveEntry(
            timestamp=datetime.now(),
            session_id=session_id,
            score=score,
            source=source,
            ccs_at_time=ccs,
        )
        self._entries.append(entry)

        if source == "mid_session":
            self._mid_session_prompted = True

        return entry

    def has_model_mismatch(self) -> bool:
        """Check whether recent sessions show consistent divergence.

        Returns True when the last `mismatch_min_sessions` end_session
        entries ALL have divergence exceeding `mismatch_threshold`.
        """
        end_entries = [e for e in self._entries if e.source == "end_session"]
        if len(end_entries) < self.mismatch_min_sessions:
            return False

        recent = end_entries[-self.mismatch_min_sessions:]
        return all(e.divergence > self.mismatch_threshold for e in recent)

    def avg_divergence(self) -> float:
        """Average divergence across all recorded entries.

        Returns 0.0 if no entries exist.
        """
        if not self._entries:
            return 0.0
        return sum(e.divergence for e in self._entries) / len(self._entries)

    def model_confidence(self) -> float:
        """Confidence that the coherence model reflects user experience.

        Derived from average divergence: lower divergence = higher
        confidence. Clamped to [0, 1].
        """
        return max(0.0, 1.0 - self.avg_divergence())

    def should_prompt_mid_session(
        self,
        prompt_count: int,
        token_estimate: int,
    ) -> bool:
        """Decide whether to ask for a mid-session coherence rating.

        Only returns True when:
        - prompt_count >= mid_session_min_prompts
        - token_estimate >= mid_session_min_tokens
        - A mid-session prompt has NOT already been issued this session

        Args:
            prompt_count: Number of prompts so far in this session.
            token_estimate: Estimated tokens processed so far.

        Returns:
            True if a mid-session rating should be requested.
        """
        if self._mid_session_prompted:
            return False
        if prompt_count < self.mid_session_min_prompts:
            return False
        if token_estimate < self.mid_session_min_tokens:
            return False
        return True

    def reset_session(self) -> None:
        """Reset per-session state for a new session.

        Clears the mid-session prompted flag so the next session
        can receive a mid-session prompt.
        """
        self._mid_session_prompted = False
