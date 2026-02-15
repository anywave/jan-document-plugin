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


@dataclass
class ArcMetrics:
    """Aggregate metrics across sessions in an arc.

    Tracks trends for CCS, entropy, RTC, and subjective scores
    across multiple sessions to detect multi-session coherence patterns.

    Attributes:
        avg_ccs: Average CCS across all completed sessions in the arc.
        ccs_trend: CCS final values per session, in order.
        entropy_trend: Entropy values per session, in order.
        rtc_trend: Return-to-coherence values per session, in order.
        subjective_trend: Subjective scores per session, in order.
        model_mismatch_count: How many sessions had model confidence
                              diverging significantly from CCS.
    """
    avg_ccs: float = 0.0
    ccs_trend: List[float] = field(default_factory=list)
    entropy_trend: List[float] = field(default_factory=list)
    rtc_trend: List[float] = field(default_factory=list)
    subjective_trend: List[float] = field(default_factory=list)
    model_mismatch_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'avg_ccs': self.avg_ccs,
            'ccs_trend': self.ccs_trend,
            'entropy_trend': self.entropy_trend,
            'rtc_trend': self.rtc_trend,
            'subjective_trend': self.subjective_trend,
            'model_mismatch_count': self.model_mismatch_count,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ArcMetrics':
        """Deserialize from dictionary."""
        return cls(
            avg_ccs=d.get('avg_ccs', 0.0),
            ccs_trend=d.get('ccs_trend', []),
            entropy_trend=d.get('entropy_trend', []),
            rtc_trend=d.get('rtc_trend', []),
            subjective_trend=d.get('subjective_trend', []),
            model_mismatch_count=d.get('model_mismatch_count', 0),
        )


@dataclass
class ArcSession:
    """A multi-session arc tracking coherence across session boundaries.

    An arc groups consecutive sessions into a coherent work unit,
    tracking how coherence evolves across session boundaries. Arcs
    auto-complete when enough sessions have been recorded, and
    suppress bloom events during the early warmup phase.

    Attributes:
        arc_id: Unique identifier (UUID).
        arc_name: Optional human-readable name for the arc.
        arc_length: Target number of sessions for this arc.
        completed_sessions: How many sessions have been added so far.
        session_ids: Ordered list of session IDs in this arc.
        metrics: Aggregate metrics across sessions.
        arc_status: 'active', 'complete', or 'interrupted'.
        created_at: When the arc was created (ISO format).
        updated_at: When the arc was last modified (ISO format).
    """
    arc_id: str
    arc_name: Optional[str]
    arc_length: int
    completed_sessions: int
    session_ids: List[str]
    metrics: ArcMetrics
    arc_status: str  # 'active' | 'complete' | 'interrupted'
    created_at: str  # ISO format
    updated_at: str  # ISO format

    @classmethod
    def create(cls, arc_length: int, name: Optional[str] = None) -> 'ArcSession':
        """Factory method to create a new active arc.

        Args:
            arc_length: Target number of sessions for the arc.
            name: Optional human-readable name.

        Returns:
            A new ArcSession in 'active' status.
        """
        now = datetime.now().isoformat()
        return cls(
            arc_id=str(uuid.uuid4()),
            arc_name=name,
            arc_length=arc_length,
            completed_sessions=0,
            session_ids=[],
            metrics=ArcMetrics(),
            arc_status='active',
            created_at=now,
            updated_at=now,
        )

    def add_session(self, session: CoherenceSession) -> None:
        """Add a completed session to this arc.

        Updates metrics from the session data. If completed_sessions
        reaches arc_length, the arc auto-completes.

        Args:
            session: A CoherenceSession that has been ended.
        """
        self.session_ids.append(session.session_id)
        self.completed_sessions += 1

        # Update CCS trend
        final_ccs = session.final_ccs if session.final_ccs is not None else 0.0
        self.metrics.ccs_trend.append(final_ccs)

        # Recalculate average CCS
        if self.metrics.ccs_trend:
            self.metrics.avg_ccs = sum(self.metrics.ccs_trend) / len(self.metrics.ccs_trend)

        # Extract subjective score from metadata if present
        subjective = session.metadata.get('subjective_score')
        if subjective is not None:
            self.metrics.subjective_trend.append(float(subjective))

        # Extract entropy from metadata if present
        entropy = session.metadata.get('entropy')
        if entropy is not None:
            self.metrics.entropy_trend.append(float(entropy))

        # Extract RTC from metadata if present
        rtc = session.metadata.get('rtc')
        if rtc is not None:
            self.metrics.rtc_trend.append(float(rtc))

        # Detect model mismatch: model_confidence in metadata vs final_ccs
        model_conf = session.metadata.get('model_confidence')
        if model_conf is not None and abs(float(model_conf) - final_ccs) > 0.2:
            self.metrics.model_mismatch_count += 1

        self.updated_at = datetime.now().isoformat()

        # Auto-complete when target reached
        if self.completed_sessions >= self.arc_length:
            self.arc_status = 'complete'

    def should_suppress_bloom(self) -> bool:
        """Whether bloom events should be suppressed.

        Bloom is suppressed during the first 3 sessions of an arc
        while the system is still establishing a multi-session baseline.

        Returns:
            True if completed_sessions < 3, meaning bloom should be suppressed.
        """
        return self.completed_sessions < 3

    def is_stale(self, max_inactive_days: int = 7) -> bool:
        """Check if the arc has been inactive too long.

        An arc is stale if it is still 'active' but its updated_at
        timestamp is older than max_inactive_days.

        Args:
            max_inactive_days: Days of inactivity before auto-interruption.

        Returns:
            True if the arc should be auto-interrupted.
        """
        if self.arc_status != 'active':
            return False
        try:
            updated = datetime.fromisoformat(self.updated_at)
            elapsed = (datetime.now() - updated).total_seconds()
            return elapsed > max_inactive_days * 86400
        except (ValueError, TypeError):
            return False

    def ccs_threshold_for_session(self, session_index: int) -> float:
        """Calculate the CCS threshold for a given session index.

        Threshold increases progressively as the arc advances,
        reflecting that later sessions should achieve higher coherence.

        Args:
            session_index: Zero-based index of the session in the arc.

        Returns:
            CCS threshold value (starts at 0.3, increases by 0.05 per session).
        """
        return 0.3 + 0.05 * session_index

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            'arc_id': self.arc_id,
            'arc_name': self.arc_name,
            'arc_length': self.arc_length,
            'completed_sessions': self.completed_sessions,
            'session_ids': self.session_ids,
            'metrics': self.metrics.to_dict(),
            'arc_status': self.arc_status,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ArcSession':
        """Deserialize from dictionary."""
        return cls(
            arc_id=d['arc_id'],
            arc_name=d.get('arc_name'),
            arc_length=d['arc_length'],
            completed_sessions=d.get('completed_sessions', 0),
            session_ids=d.get('session_ids', []),
            metrics=ArcMetrics.from_dict(d.get('metrics', {})),
            arc_status=d.get('arc_status', 'active'),
            created_at=d['created_at'],
            updated_at=d['updated_at'],
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
        self._active_arc: Optional[ArcSession] = None

    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> CoherenceSession:
        """Start a new coherence session.

        If there is an active session, ends it first (persisting to disk).
        Also checks for stale arcs and auto-interrupts them.

        Args:
            metadata: Optional metadata to attach to the session.

        Returns:
            The newly created session.
        """
        if self.active_session is not None:
            self.end_session()

        # Auto-interrupt stale arcs (7+ days inactive)
        self._check_arc_staleness()

        self.active_session = CoherenceSession.create(metadata=metadata)
        return self.active_session

    def end_session(self) -> Optional[CoherenceSession]:
        """End the active session and persist it.

        If an arc is active, the ended session is automatically attached to it.

        Returns:
            The ended session, or None if no session was active.
        """
        if self.active_session is None:
            return None

        self.active_session.end()
        self._persist_session(self.active_session)
        ended = self.active_session

        # Auto-attach to active arc
        if self._active_arc is not None and self._active_arc.arc_status == 'active':
            self._active_arc.add_session(ended)
            self._persist_arcs()

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

        # Compute duration in seconds from started_at ISO string
        duration_s = 0.0
        try:
            started = datetime.fromisoformat(self.active_session.started_at)
            duration_s = (datetime.now() - started).total_seconds()
        except (ValueError, TypeError):
            pass

        return {
            'active': True,
            'session_id': self.active_session.session_id,
            'phase': self.active_session.phase.value,
            'started_at': self.active_session.started_at,
            'duration_s': round(duration_s, 1),
            'prompt_count': self.active_session.prompt_count,
            'peak_ccs': self.active_session.peak_ccs,
            'ccs_readings': len(self.active_session.ccs_history),
        }

    @property
    def active_arc(self) -> Optional[ArcSession]:
        """The currently active arc, if any."""
        return self._active_arc

    def start_arc(self, arc_length: int, name: Optional[str] = None) -> ArcSession:
        """Start a new multi-session arc.

        If there is an existing active arc, it is interrupted first.

        Args:
            arc_length: Target number of sessions for the arc.
            name: Optional human-readable name.

        Returns:
            The newly created ArcSession.
        """
        if self._active_arc is not None and self._active_arc.arc_status == 'active':
            self._active_arc.arc_status = 'interrupted'
            self._active_arc.updated_at = datetime.now().isoformat()

        self._active_arc = ArcSession.create(arc_length, name)
        self._persist_arcs()
        return self._active_arc

    def end_arc(self) -> Optional[ArcSession]:
        """Manually close the active arc.

        Sets status to 'complete' regardless of completed_sessions count.

        Returns:
            The ended arc, or None if no arc was active.
        """
        if self._active_arc is None:
            return None

        self._active_arc.arc_status = 'complete'
        self._active_arc.updated_at = datetime.now().isoformat()
        self._persist_arcs()
        ended = self._active_arc
        self._active_arc = None
        return ended

    def _check_arc_staleness(self) -> None:
        """Auto-interrupt any active arc that has been inactive for 7+ days."""
        if self._active_arc is not None and self._active_arc.is_stale():
            self._active_arc.arc_status = 'interrupted'
            self._active_arc.updated_at = datetime.now().isoformat()
            self._persist_arcs()
            self._active_arc = None

    def get_arc_status(self) -> Dict[str, Any]:
        """Get current arc status.

        Returns:
            Dict with arc info, or minimal dict if no active arc.
        """
        # Auto-interrupt stale arcs on status check
        self._check_arc_staleness()

        if self._active_arc is None:
            return {
                'active': False,
                'arc_id': None,
            }

        return {
            'active': self._active_arc.arc_status == 'active',
            'arc_id': self._active_arc.arc_id,
            'arc_name': self._active_arc.arc_name,
            'arc_status': self._active_arc.arc_status,
            'arc_length': self._active_arc.arc_length,
            'completed_sessions': self._active_arc.completed_sessions,
            'avg_ccs': self._active_arc.metrics.avg_ccs,
            'suppress_bloom': self._active_arc.should_suppress_bloom(),
        }

    def _persist_arcs(self) -> Path:
        """Write arc data to arcs.json in sessions_dir.

        Loads existing arcs from disk, updates/adds the current arc,
        and writes back.

        Returns:
            Path to the written JSON file.
        """
        filepath = self.sessions_dir / "arcs.json"
        arcs_data: List[Dict[str, Any]] = []

        # Load existing arcs
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    arcs_data = json.load(f)
            except (json.JSONDecodeError, ValueError):
                arcs_data = []

        if self._active_arc is not None:
            arc_dict = self._active_arc.to_dict()
            # Update existing or append
            found = False
            for i, existing in enumerate(arcs_data):
                if existing.get('arc_id') == self._active_arc.arc_id:
                    arcs_data[i] = arc_dict
                    found = True
                    break
            if not found:
                arcs_data.append(arc_dict)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(arcs_data, f, indent=2)

        return filepath

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
