"""
Session lifecycle management for coherence engine.

Tracks coherence sessions through three phases:
- DISSOLVE: Initial state, high uncertainty, establishing baseline
- PROCESS: Stable readings, active coherence tracking
- RECONSTITUTE: Rising coherence trend, session nearing productive end

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import uuid


class SessionPhase(Enum):
    """Three-phase session lifecycle.

    DISSOLVE -> PROCESS -> RECONSTITUTE

    Named after the alchemical stages: the initial dissolution of old
    patterns, the processing/transformation, and the reconstitution
    into a new coherent whole.
    """
    DISSOLVE = "dissolve"
    PROCESS = "process"
    RECONSTITUTE = "reconstitute"


@dataclass
class CoherenceSession:
    """A single coherence session tracking CCS over time.

    Attributes:
        session_id: Unique identifier for this session.
        phase: Current session phase.
        started_at: When the session began.
        ended_at: When the session ended (None if active).
        ccs_history: List of (timestamp_iso, ccs_value) tuples.
        peak_ccs: Highest CCS observed this session.
        prompt_count: Number of prompts processed.
        token_estimate: Estimated total tokens processed.
        final_ccs: CCS at session end.
        metadata: Arbitrary metadata attached at creation.
    """
    session_id: str
    phase: SessionPhase
    started_at: str  # ISO format
    ended_at: Optional[str] = None  # ISO format
    ccs_history: List[Tuple[str, float]] = field(default_factory=list)
    peak_ccs: float = 0.0
    prompt_count: int = 0
    token_estimate: int = 0
    final_ccs: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, metadata: Optional[Dict[str, Any]] = None) -> 'CoherenceSession':
        """Factory method to create a new session in DISSOLVE phase."""
        return cls(
            session_id=str(uuid.uuid4()),
            phase=SessionPhase.DISSOLVE,
            started_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )

    def record_ccs(self, ccs: float) -> None:
        """Record a CCS reading.

        Appends to history and updates peak if this is the highest reading.

        Args:
            ccs: Composite Coherence Score, 0.0 to 1.0.
        """
        timestamp = datetime.now().isoformat()
        self.ccs_history.append((timestamp, ccs))
        if ccs > self.peak_ccs:
            self.peak_ccs = ccs

    def record_prompt(self, token_count: int) -> None:
        """Record a prompt being processed.

        Args:
            token_count: Estimated token count for this prompt.
        """
        self.prompt_count += 1
        self.token_estimate += token_count

    def check_phase_transition(self) -> Optional[SessionPhase]:
        """Check if a phase transition should occur.

        Transition rules:
        - DISSOLVE -> PROCESS: When 3+ CCS readings exist and the last 3
          are within +/-0.05 of each other (stability detected).
        - PROCESS -> RECONSTITUTE: When CCS shows a rising trend AND
          prompt_count > 5.

        Returns:
            The new phase if a transition occurred, None otherwise.
        """
        if self.phase == SessionPhase.DISSOLVE:
            return self._check_dissolve_to_process()
        elif self.phase == SessionPhase.PROCESS:
            return self._check_process_to_reconstitute()
        return None

    def _check_dissolve_to_process(self) -> Optional[SessionPhase]:
        """DISSOLVE -> PROCESS when last 3 readings are within +/-0.05."""
        if len(self.ccs_history) < 3:
            return None

        recent_values = [v for _, v in self.ccs_history[-3:]]
        min_val = min(recent_values)
        max_val = max(recent_values)

        if (max_val - min_val) <= 0.05:
            self.phase = SessionPhase.PROCESS
            return SessionPhase.PROCESS

        return None

    def _check_process_to_reconstitute(self) -> Optional[SessionPhase]:
        """PROCESS -> RECONSTITUTE when CCS trending up AND prompt_count > 5."""
        if self.prompt_count <= 5:
            return None

        if len(self.ccs_history) < 3:
            return None

        # Check for rising trend: each of last 3 readings >= previous
        recent_values = [v for _, v in self.ccs_history[-3:]]
        is_rising = all(
            recent_values[i] >= recent_values[i - 1]
            for i in range(1, len(recent_values))
        )

        if is_rising:
            self.phase = SessionPhase.RECONSTITUTE
            return SessionPhase.RECONSTITUTE

        return None

    def force_phase(self, phase: SessionPhase) -> None:
        """Force the session into a specific phase.

        Args:
            phase: The phase to set.
        """
        self.phase = phase

    def end(self) -> None:
        """End the session.

        Sets ended_at timestamp and final_ccs from last reading.
        """
        self.ended_at = datetime.now().isoformat()
        if self.ccs_history:
            self.final_ccs = self.ccs_history[-1][1]
        else:
            self.final_ccs = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'session_id': self.session_id,
            'phase': self.phase.value,
            'started_at': self.started_at,
            'ended_at': self.ended_at,
            'ccs_history': self.ccs_history,
            'peak_ccs': self.peak_ccs,
            'prompt_count': self.prompt_count,
            'token_estimate': self.token_estimate,
            'final_ccs': self.final_ccs,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CoherenceSession':
        """Deserialize from dictionary."""
        # Convert ccs_history from list-of-lists (JSON) back to list-of-tuples
        ccs_history = [(ts, val) for ts, val in d.get('ccs_history', [])]
        return cls(
            session_id=d['session_id'],
            phase=SessionPhase(d['phase']),
            started_at=d['started_at'],
            ended_at=d.get('ended_at'),
            ccs_history=ccs_history,
            peak_ccs=d.get('peak_ccs', 0.0),
            prompt_count=d.get('prompt_count', 0),
            token_estimate=d.get('token_estimate', 0),
            final_ccs=d.get('final_ccs'),
            metadata=d.get('metadata', {}),
        )


class SessionManager:
    """Manages coherence session lifecycle and persistence.

    Handles creating, tracking, and persisting sessions to disk.
    Only one session can be active at a time.

    Args:
        sessions_dir: Path to directory for session JSON files.
                      Created if it does not exist.
    """

    def __init__(self, sessions_dir: str) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.active_session: Optional[CoherenceSession] = None

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> CoherenceSession:
        """Start a new coherence session.

        If there is an active session, ends it first (persisting to disk).

        Args:
            metadata: Optional metadata to attach to the session.

        Returns:
            The newly created session.
        """
        if self.active_session is not None:
            self.end_session()

        self.active_session = CoherenceSession.create(metadata=metadata)
        return self.active_session

    def end_session(self) -> Optional[CoherenceSession]:
        """End the active session and persist it.

        Returns:
            The ended session, or None if no session was active.
        """
        if self.active_session is None:
            return None

        self.active_session.end()
        self._persist_session(self.active_session)
        ended = self.active_session
        self.active_session = None
        return ended

    def record_ccs(self, ccs: float) -> Optional[SessionPhase]:
        """Record a CCS reading in the active session.

        Args:
            ccs: Composite Coherence Score.

        Returns:
            The new phase if a transition occurred, None otherwise.
            Returns None if no active session.
        """
        if self.active_session is None:
            return None

        self.active_session.record_ccs(ccs)
        return self.active_session.check_phase_transition()

    def record_prompt(self, token_count: int) -> None:
        """Record a prompt in the active session.

        Args:
            token_count: Estimated token count.
        """
        if self.active_session is not None:
            self.active_session.record_prompt(token_count)

    def get_status(self) -> Dict[str, Any]:
        """Get current session status.

        Returns:
            Dict with session info, or minimal dict if no active session.
        """
        if self.active_session is None:
            return {
                'active': False,
                'session_id': None,
                'phase': None,
            }

        return {
            'active': True,
            'session_id': self.active_session.session_id,
            'phase': self.active_session.phase.value,
            'started_at': self.active_session.started_at,
            'prompt_count': self.active_session.prompt_count,
            'peak_ccs': self.active_session.peak_ccs,
            'ccs_readings': len(self.active_session.ccs_history),
        }

    def _persist_session(self, session: CoherenceSession) -> Path:
        """Write session data to a JSON file.

        Args:
            session: The session to persist.

        Returns:
            Path to the written JSON file.
        """
        filename = f"session_{session.session_id}.json"
        filepath = self.sessions_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2)
        return filepath

    def load_recent_sessions(self, count: int = 10) -> List[CoherenceSession]:
        """Load the most recent persisted sessions from disk.

        Sessions are sorted by started_at descending (most recent first).

        Args:
            count: Maximum number of sessions to load.

        Returns:
            List of CoherenceSession objects, most recent first.
        """
        sessions = []
        session_files = sorted(
            self.sessions_dir.glob("session_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        for filepath in session_files[:count]:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sessions.append(CoherenceSession.from_dict(data))
            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip corrupt files
                continue

        return sessions
