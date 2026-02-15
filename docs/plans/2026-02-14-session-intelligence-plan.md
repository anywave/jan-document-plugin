# Session Intelligence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement all 6 Architect Message 12 outputs into the MOBIUS coherence engine — session lifecycle, subjective scoring, SCOUTER classification, arc tracking, model confidence, and Kuramoto network coupling.

**Architecture:** Hybrid approach — core logic (session, scouter, arcs, network) in Python engine at `extensions/coherence-glove/coherence/`, frontend UX (subjective prompt) in TypeScript at `web-app/src/`. All new features exposed via MCP tools added to existing `mcp_server.py`.

**Tech Stack:** Python 3.12 (engine), TypeScript/React (frontend), JSON-RPC stdio (MCP), Zustand (state), JSON files (persistence)

**Base paths:**
- Engine: `C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove/`
- Frontend: `C:/ANYWAVEREPO/jan-ai-fork/web-app/src/`
- Tests: `C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove/tests/`

**Test runner:** `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/ -v`

---

## Task 1: Test Infrastructure Setup

**Files:**
- Create: `extensions/coherence-glove/tests/__init__.py`
- Create: `extensions/coherence-glove/tests/conftest.py`

**Step 1: Create test directory and conftest**

```python
# tests/__init__.py
# (empty)
```

```python
# tests/conftest.py
"""Shared fixtures for coherence engine tests."""
import sys
import os
import pytest
import numpy as np
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.multiwave_state import MultiWaveCoherenceState


@pytest.fixture
def default_state():
    """A neutral coherence state for testing."""
    return MultiWaveCoherenceState.create_default()


@pytest.fixture
def healthy_state():
    """A healthy coherence state (CCS > 0.6)."""
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=np.array([0.6, 0.7, 0.8, 0.65, 0.55]),
        band_phases=np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
        signal_coherences={'text': 0.7, 'breath': 0.8},
        intentionality=0.7,
        breath_entrained=True,
        breath_rate_hz=0.1,
        scalar_coherence=0.72,
        uncertainty=0.15,
    )


@pytest.fixture
def unstable_state():
    """An unstable coherence state (CCS < 0.3)."""
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=np.array([0.1, 0.15, 0.2, 0.12, 0.08]),
        band_phases=np.array([1.0, 2.5, 0.3, 4.1, 5.8]),
        signal_coherences={'text': 0.2},
        intentionality=0.1,
        breath_entrained=False,
        breath_rate_hz=0.05,
        scalar_coherence=0.15,
        uncertainty=0.7,
    )
```

**Step 2: Verify pytest runs**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/ -v --collect-only`
Expected: "no tests ran" (0 collected, no errors)

**Step 3: Commit**

```bash
git add extensions/coherence-glove/tests/
git commit -m "feat: add test infrastructure for coherence engine"
```

---

## Task 2: Session Lifecycle — Data Model

**Files:**
- Create: `extensions/coherence-glove/coherence/session.py`
- Create: `extensions/coherence-glove/tests/test_session.py`

**Step 1: Write failing tests for session data model**

```python
# tests/test_session.py
"""Tests for session lifecycle management."""
import pytest
from datetime import datetime, timedelta
from coherence.session import (
    SessionPhase,
    CoherenceSession,
    SessionManager,
)


class TestCoherenceSession:
    def test_create_session(self):
        session = CoherenceSession.create()
        assert session.session_id is not None
        assert session.phase == SessionPhase.DISSOLVE
        assert session.prompt_count == 0
        assert session.token_estimate == 0
        assert session.ended_at is None
        assert session.peak_ccs == 0.0

    def test_record_ccs(self):
        session = CoherenceSession.create()
        session.record_ccs(0.5)
        session.record_ccs(0.7)
        session.record_ccs(0.3)
        assert session.peak_ccs == 0.7
        assert len(session.coherence_history) == 3

    def test_record_prompt(self):
        session = CoherenceSession.create()
        session.record_prompt(token_count=150)
        session.record_prompt(token_count=200)
        assert session.prompt_count == 2
        assert session.token_estimate == 350

    def test_end_session(self):
        session = CoherenceSession.create()
        session.record_ccs(0.6)
        session.end()
        assert session.ended_at is not None
        assert session.final_ccs == 0.6

    def test_to_dict_roundtrip(self):
        session = CoherenceSession.create()
        session.record_ccs(0.5)
        session.record_prompt(token_count=100)
        d = session.to_dict()
        restored = CoherenceSession.from_dict(d)
        assert restored.session_id == session.session_id
        assert restored.prompt_count == 1
        assert restored.token_estimate == 100


class TestSessionPhaseTransitions:
    def test_dissolve_to_process(self):
        """PROCESS triggered when CCS stabilizes: 3+ readings within +/-0.05."""
        session = CoherenceSession.create()
        assert session.phase == SessionPhase.DISSOLVE
        # 3 stable readings
        session.record_ccs(0.50)
        session.record_ccs(0.52)
        session.record_ccs(0.49)
        session.check_phase_transition()
        assert session.phase == SessionPhase.PROCESS

    def test_no_transition_without_stability(self):
        """No transition if CCS is volatile."""
        session = CoherenceSession.create()
        session.record_ccs(0.50)
        session.record_ccs(0.80)
        session.record_ccs(0.30)
        session.check_phase_transition()
        assert session.phase == SessionPhase.DISSOLVE

    def test_process_to_reconstitute(self):
        """RECONSTITUTE when CCS trend rising AND prompt_count > 5."""
        session = CoherenceSession.create()
        # Force into PROCESS
        session.phase = SessionPhase.PROCESS
        for i in range(6):
            session.record_prompt(token_count=100)
        # Rising CCS trend
        for v in [0.4, 0.45, 0.5, 0.55, 0.6]:
            session.record_ccs(v)
        session.check_phase_transition()
        assert session.phase == SessionPhase.RECONSTITUTE

    def test_force_reconstitute(self):
        """Manual force to RECONSTITUTE."""
        session = CoherenceSession.create()
        session.force_phase(SessionPhase.RECONSTITUTE)
        assert session.phase == SessionPhase.RECONSTITUTE
```

**Step 2: Run tests to verify they fail**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_session.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'coherence.session'`

**Step 3: Implement session data model**

```python
# coherence/session.py
"""
Session Lifecycle Management.

Tracks coherence sessions with phase transitions:
  DISSOLVE -> PROCESS -> RECONSTITUTE

Maps to the Architect's alchemical model:
  Solve (dissolve) -> Bounded recursion -> Coagula (reconstitute)

(c) 2026 Anywave Creations
MIT License
"""

import uuid
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum


class SessionPhase(Enum):
    DISSOLVE = "dissolve"
    PROCESS = "process"
    RECONSTITUTE = "reconstitute"


@dataclass
class CoherenceSession:
    session_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    phase: SessionPhase = SessionPhase.DISSOLVE
    prompt_count: int = 0
    token_estimate: int = 0
    coherence_history: List[float] = field(default_factory=list)
    peak_ccs: float = 0.0
    final_ccs: float = 0.0
    subjective_score: Optional[float] = None
    scouter_events: List[dict] = field(default_factory=list)
    model_confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Phase transition thresholds
    _stability_window: int = 3
    _stability_tolerance: float = 0.05
    _reconstitute_min_prompts: int = 5

    @classmethod
    def create(cls) -> 'CoherenceSession':
        return cls(
            session_id=str(uuid.uuid4()),
            started_at=datetime.now(),
        )

    def record_ccs(self, ccs: float) -> None:
        self.coherence_history.append(ccs)
        if ccs > self.peak_ccs:
            self.peak_ccs = ccs
        self.final_ccs = ccs

    def record_prompt(self, token_count: int = 0) -> None:
        self.prompt_count += 1
        self.token_estimate += token_count

    def check_phase_transition(self) -> Optional[SessionPhase]:
        old_phase = self.phase
        if self.phase == SessionPhase.DISSOLVE:
            self._check_dissolve_to_process()
        elif self.phase == SessionPhase.PROCESS:
            self._check_process_to_reconstitute()
        if self.phase != old_phase:
            return self.phase
        return None

    def _check_dissolve_to_process(self) -> None:
        if len(self.coherence_history) < self._stability_window:
            return
        recent = self.coherence_history[-self._stability_window:]
        spread = max(recent) - min(recent)
        if spread <= self._stability_tolerance:
            self.phase = SessionPhase.PROCESS

    def _check_process_to_reconstitute(self) -> None:
        if self.prompt_count <= self._reconstitute_min_prompts:
            return
        if len(self.coherence_history) < 3:
            return
        recent = self.coherence_history[-5:] if len(self.coherence_history) >= 5 else self.coherence_history
        if len(recent) >= 3:
            rising = all(recent[i] <= recent[i + 1] for i in range(len(recent) - 1))
            if rising:
                self.phase = SessionPhase.RECONSTITUTE

    def force_phase(self, phase: SessionPhase) -> None:
        self.phase = phase

    def end(self) -> None:
        self.ended_at = datetime.now()
        if self.coherence_history:
            self.final_ccs = self.coherence_history[-1]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'session_id': self.session_id,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
            'phase': self.phase.value,
            'prompt_count': self.prompt_count,
            'token_estimate': self.token_estimate,
            'coherence_history': self.coherence_history,
            'peak_ccs': self.peak_ccs,
            'final_ccs': self.final_ccs,
            'subjective_score': self.subjective_score,
            'scouter_events': self.scouter_events,
            'model_confidence': self.model_confidence,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'CoherenceSession':
        session = cls(
            session_id=d['session_id'],
            started_at=datetime.fromisoformat(d['started_at']),
        )
        session.ended_at = datetime.fromisoformat(d['ended_at']) if d.get('ended_at') else None
        session.phase = SessionPhase(d.get('phase', 'dissolve'))
        session.prompt_count = d.get('prompt_count', 0)
        session.token_estimate = d.get('token_estimate', 0)
        session.coherence_history = d.get('coherence_history', [])
        session.peak_ccs = d.get('peak_ccs', 0.0)
        session.final_ccs = d.get('final_ccs', 0.0)
        session.subjective_score = d.get('subjective_score')
        session.scouter_events = d.get('scouter_events', [])
        session.model_confidence = d.get('model_confidence', 1.0)
        session.metadata = d.get('metadata', {})
        return session


class SessionManager:
    """Manages coherence session lifecycle and persistence."""

    def __init__(self, sessions_dir: Optional[str] = None):
        self._active_session: Optional[CoherenceSession] = None
        self._sessions_dir = sessions_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'sessions'
        )
        self._on_session_end: Optional[Callable[[CoherenceSession], None]] = None
        os.makedirs(self._sessions_dir, exist_ok=True)

    @property
    def active_session(self) -> Optional[CoherenceSession]:
        return self._active_session

    @property
    def has_active_session(self) -> bool:
        return self._active_session is not None

    def start_session(self, metadata: Optional[Dict] = None) -> CoherenceSession:
        if self._active_session is not None:
            self.end_session()
        session = CoherenceSession.create()
        if metadata:
            session.metadata = metadata
        self._active_session = session
        return session

    def end_session(self) -> Optional[CoherenceSession]:
        if self._active_session is None:
            return None
        session = self._active_session
        session.end()
        self._persist_session(session)
        self._active_session = None
        if self._on_session_end:
            self._on_session_end(session)
        return session

    def record_ccs(self, ccs: float) -> Optional[SessionPhase]:
        if self._active_session is None:
            return None
        self._active_session.record_ccs(ccs)
        return self._active_session.check_phase_transition()

    def record_prompt(self, token_count: int = 0) -> None:
        if self._active_session is None:
            return
        self._active_session.record_prompt(token_count)

    def get_status(self) -> Dict[str, Any]:
        if self._active_session is None:
            return {'active': False}
        s = self._active_session
        return {
            'active': True,
            'session_id': s.session_id,
            'phase': s.phase.value,
            'prompt_count': s.prompt_count,
            'token_estimate': s.token_estimate,
            'peak_ccs': s.peak_ccs,
            'current_ccs': s.final_ccs,
            'model_confidence': s.model_confidence,
            'duration_s': (datetime.now() - s.started_at).total_seconds(),
        }

    def _persist_session(self, session: CoherenceSession) -> None:
        filename = f"{session.started_at.strftime('%Y%m%d_%H%M%S')}_{session.session_id[:8]}.json"
        filepath = os.path.join(self._sessions_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(session.to_dict(), f, indent=2)

    def load_recent_sessions(self, count: int = 10) -> List[CoherenceSession]:
        sessions = []
        if not os.path.exists(self._sessions_dir):
            return sessions
        files = sorted(
            [f for f in os.listdir(self._sessions_dir) if f.endswith('.json') and f != 'arcs.json'],
            reverse=True
        )
        for f in files[:count]:
            try:
                with open(os.path.join(self._sessions_dir, f)) as fh:
                    sessions.append(CoherenceSession.from_dict(json.load(fh)))
            except (json.JSONDecodeError, KeyError):
                continue
        return sessions
```

**Step 4: Run tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_session.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add extensions/coherence-glove/coherence/session.py extensions/coherence-glove/tests/test_session.py
git commit -m "feat: add session lifecycle with phase transitions (dissolve/process/reconstitute)"
```

---

## Task 3: SessionManager Tests

**Files:**
- Modify: `extensions/coherence-glove/tests/test_session.py`

**Step 1: Add SessionManager tests**

Append to `tests/test_session.py`:

```python
class TestSessionManager:
    def test_start_session(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        session = mgr.start_session()
        assert mgr.has_active_session
        assert session.session_id is not None

    def test_end_session_persists(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        mgr.start_session()
        mgr.record_ccs(0.5)
        ended = mgr.end_session()
        assert ended is not None
        assert not mgr.has_active_session
        # Check file was written
        files = list(tmp_path.glob('*.json'))
        assert len(files) == 1

    def test_start_new_ends_previous(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        s1 = mgr.start_session()
        s2 = mgr.start_session()
        assert s1.session_id != s2.session_id
        assert s1.ended_at is not None

    def test_record_ccs_triggers_phase_transition(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        mgr.start_session()
        mgr.record_ccs(0.50)
        mgr.record_ccs(0.52)
        new_phase = mgr.record_ccs(0.49)
        assert new_phase == SessionPhase.PROCESS

    def test_get_status_no_session(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        status = mgr.get_status()
        assert status['active'] is False

    def test_load_recent_sessions(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        mgr.start_session()
        mgr.record_ccs(0.5)
        mgr.end_session()
        mgr.start_session()
        mgr.record_ccs(0.6)
        mgr.end_session()
        loaded = mgr.load_recent_sessions(count=5)
        assert len(loaded) == 2
```

**Step 2: Run tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_session.py -v`
Expected: All 13 tests PASS

**Step 3: Commit**

```bash
git add extensions/coherence-glove/tests/test_session.py
git commit -m "test: add SessionManager persistence and lifecycle tests"
```

---

## Task 4: Subjective Coherence Score

**Files:**
- Create: `extensions/coherence-glove/coherence/subjective.py`
- Create: `extensions/coherence-glove/tests/test_subjective.py`

**Step 1: Write failing tests**

```python
# tests/test_subjective.py
"""Tests for subjective coherence scoring."""
import pytest
from datetime import datetime
from coherence.subjective import SubjectiveEntry, SubjectiveTracker


class TestSubjectiveEntry:
    def test_create_entry(self):
        entry = SubjectiveEntry(
            timestamp=datetime.now(),
            session_id='test-123',
            score=7.0,
            source='mid_session',
            ccs_at_time=0.65,
        )
        assert entry.divergence == pytest.approx(0.05, abs=0.01)

    def test_divergence_calculation(self):
        """Divergence = abs(score/10 - ccs)."""
        entry = SubjectiveEntry(
            timestamp=datetime.now(),
            session_id='test',
            score=3.0,  # normalized: 0.3
            source='end_session',
            ccs_at_time=0.8,  # divergence = |0.3 - 0.8| = 0.5
        )
        assert entry.divergence == pytest.approx(0.5, abs=0.01)


class TestSubjectiveTracker:
    def test_record_score(self):
        tracker = SubjectiveTracker()
        tracker.record('session-1', score=7.0, source='mid_session', ccs=0.65)
        assert len(tracker.entries) == 1

    def test_model_mismatch_detection(self):
        """Mismatch flagged when divergence > 0.3 for 3+ sessions."""
        tracker = SubjectiveTracker()
        # 3 sessions with high divergence
        tracker.record('s1', score=2.0, source='end_session', ccs=0.8)  # div=0.6
        tracker.record('s2', score=1.0, source='end_session', ccs=0.7)  # div=0.6
        tracker.record('s3', score=3.0, source='end_session', ccs=0.9)  # div=0.6
        assert tracker.has_model_mismatch()

    def test_no_mismatch_when_aligned(self):
        tracker = SubjectiveTracker()
        tracker.record('s1', score=7.0, source='end_session', ccs=0.7)
        tracker.record('s2', score=6.0, source='end_session', ccs=0.6)
        tracker.record('s3', score=8.0, source='end_session', ccs=0.8)
        assert not tracker.has_model_mismatch()

    def test_average_divergence(self):
        tracker = SubjectiveTracker()
        tracker.record('s1', score=5.0, source='end_session', ccs=0.5)  # div=0.0
        tracker.record('s2', score=5.0, source='end_session', ccs=0.7)  # div=0.2
        assert tracker.avg_divergence() == pytest.approx(0.1, abs=0.01)

    def test_should_prompt_mid_session(self):
        tracker = SubjectiveTracker()
        assert not tracker.should_prompt_mid_session(prompt_count=2, token_estimate=500)
        assert not tracker.should_prompt_mid_session(prompt_count=3, token_estimate=500)
        assert not tracker.should_prompt_mid_session(prompt_count=2, token_estimate=1000)
        assert tracker.should_prompt_mid_session(prompt_count=3, token_estimate=1000)

    def test_no_duplicate_mid_session_prompt(self):
        tracker = SubjectiveTracker()
        assert tracker.should_prompt_mid_session(prompt_count=3, token_estimate=1000)
        tracker.record('s1', score=5.0, source='mid_session', ccs=0.5)
        assert not tracker.should_prompt_mid_session(prompt_count=5, token_estimate=2000)
```

**Step 2: Run to verify failure**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_subjective.py -v`
Expected: FAIL

**Step 3: Implement**

```python
# coherence/subjective.py
"""
Subjective Coherence Score tracking.

Captures user self-reported coherence (0-10) and computes divergence
from measured CCS for epistemic humility / model mismatch detection.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SubjectiveEntry:
    timestamp: datetime
    session_id: str
    score: float       # 0-10
    source: str        # "mid_session" | "end_session"
    ccs_at_time: float

    @property
    def divergence(self) -> float:
        normalized = self.score / 10.0
        return abs(normalized - self.ccs_at_time)

    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp.isoformat(),
            'session_id': self.session_id,
            'score': self.score,
            'source': self.source,
            'ccs_at_time': self.ccs_at_time,
            'divergence': self.divergence,
        }


class SubjectiveTracker:
    """Tracks subjective coherence scores and detects model mismatch."""

    def __init__(self,
                 mismatch_threshold: float = 0.3,
                 mismatch_min_sessions: int = 3,
                 mid_session_min_prompts: int = 3,
                 mid_session_min_tokens: int = 1000):
        self.entries: List[SubjectiveEntry] = []
        self.mismatch_threshold = mismatch_threshold
        self.mismatch_min_sessions = mismatch_min_sessions
        self.mid_session_min_prompts = mid_session_min_prompts
        self.mid_session_min_tokens = mid_session_min_tokens
        self._mid_session_prompted = False

    def record(self, session_id: str, score: float, source: str, ccs: float) -> SubjectiveEntry:
        entry = SubjectiveEntry(
            timestamp=datetime.now(),
            session_id=session_id,
            score=max(0.0, min(10.0, score)),
            source=source,
            ccs_at_time=ccs,
        )
        self.entries.append(entry)
        if source == 'mid_session':
            self._mid_session_prompted = True
        return entry

    def has_model_mismatch(self) -> bool:
        end_entries = [e for e in self.entries if e.source == 'end_session']
        if len(end_entries) < self.mismatch_min_sessions:
            return False
        recent = end_entries[-self.mismatch_min_sessions:]
        return all(e.divergence > self.mismatch_threshold for e in recent)

    def avg_divergence(self) -> float:
        if not self.entries:
            return 0.0
        return sum(e.divergence for e in self.entries) / len(self.entries)

    def model_confidence(self) -> float:
        return max(0.0, 1.0 - self.avg_divergence())

    def should_prompt_mid_session(self, prompt_count: int, token_estimate: int) -> bool:
        if self._mid_session_prompted:
            return False
        return (prompt_count >= self.mid_session_min_prompts and
                token_estimate >= self.mid_session_min_tokens)

    def reset_session(self) -> None:
        self._mid_session_prompted = False
```

**Step 4: Run tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_subjective.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add extensions/coherence-glove/coherence/subjective.py extensions/coherence-glove/tests/test_subjective.py
git commit -m "feat: add subjective coherence score with divergence tracking"
```

---

## Task 5: SCOUTER 3-Class Destabilization Model

**Files:**
- Create: `extensions/coherence-glove/coherence/scouter.py`
- Create: `extensions/coherence-glove/tests/test_scouter.py`

**Step 1: Write failing tests**

```python
# tests/test_scouter.py
"""Tests for SCOUTER 3-class destabilization classifier."""
import pytest
import numpy as np
from datetime import datetime
from coherence.scouter import Scouter, DestabilizationClass
from coherence.multiwave_state import MultiWaveCoherenceState


def make_state(ccs: float, hr_stable: bool = True) -> MultiWaveCoherenceState:
    amps = np.array([0.5, 0.6, 0.7, 0.5, 0.4]) if hr_stable else np.array([0.1, 0.2, 0.3, 0.9, 0.1])
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=amps,
        band_phases=np.zeros(5),
        signal_coherences={'text': ccs},
        intentionality=0.5,
        breath_entrained=hr_stable,
        breath_rate_hz=0.1,
        scalar_coherence=ccs,
        uncertainty=1.0 - ccs,
    )


class TestScouter:
    def test_stable_classification(self):
        scouter = Scouter()
        # Feed stable CCS values
        for _ in range(10):
            result = scouter.classify(make_state(0.7))
        assert result == DestabilizationClass.STABLE

    def test_noise_classification(self):
        """Random spike with quick recovery = Class A (noise)."""
        scouter = Scouter()
        # Establish baseline
        for _ in range(30):
            scouter.classify(make_state(0.7))
        # Single random spike
        scouter.classify(make_state(0.3))
        # Quick recovery
        result = scouter.classify(make_state(0.68))
        assert result == DestabilizationClass.NOISE

    def test_psi_echo_index_low_for_noise(self):
        scouter = Scouter()
        for _ in range(30):
            scouter.classify(make_state(0.7))
        scouter.classify(make_state(0.3))
        scouter.classify(make_state(0.69))
        assert scouter.psi_echo_index < 0.3

    def test_shadow_classification(self):
        """Structured echo pattern with physiological stability = Class B."""
        scouter = Scouter()
        # Establish baseline
        for _ in range(10):
            scouter.classify(make_state(0.7))
        # Oscillating pattern (structured perturbation with echo)
        for _ in range(25):
            scouter.classify(make_state(0.45))
            scouter.classify(make_state(0.50))
        result = scouter.classify(make_state(0.47))
        assert result == DestabilizationClass.SHADOW

    def test_trauma_classification(self):
        """HR spike + breath irregularity + rising entropy = Class C."""
        scouter = Scouter()
        for _ in range(10):
            scouter.classify(make_state(0.7))
        # Rapid deterioration with physiological instability
        for i in range(5):
            result = scouter.classify(make_state(0.7 - i * 0.12, hr_stable=False))
        assert result == DestabilizationClass.TRAUMA

    def test_to_dict(self):
        scouter = Scouter()
        scouter.classify(make_state(0.5))
        d = scouter.get_status()
        assert 'classification' in d
        assert 'psi_echo_index' in d
        assert 'confidence' in d
```

**Step 2: Run to verify failure**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_scouter.py -v`
Expected: FAIL

**Step 3: Implement SCOUTER**

```python
# coherence/scouter.py
"""
SCOUTER — 3-Class Destabilization Classifier.

Classifies coherence perturbations into:
  Class A (NOISE):  Random entropy spike, low autocorrelation, quick recovery
  Class B (SHADOW): Structured echo pattern, moderate entropy, physiologically stable
  Class C (TRAUMA): HR spike, breath irregularity, entropy rising rapidly

Key metric: psi_echo_index — autocorrelation of CCS over 60s echo buffer.
High autocorrelation = structured (shadow); low = random (noise).

Sits upstream of crisis_detection.py — classifies perturbation TYPE
before deciding response strategy.

(c) 2026 Anywave Creations
MIT License
"""

from collections import deque
from enum import Enum
from typing import Dict, Any, Optional
import numpy as np

from .multiwave_state import MultiWaveCoherenceState


class DestabilizationClass(Enum):
    STABLE = "stable"
    NOISE = "noise"       # Class A
    SHADOW = "shadow"     # Class B
    TRAUMA = "trauma"     # Class C


class Scouter:
    """3-class destabilization classifier using psi_echo_index."""

    def __init__(self,
                 buffer_size: int = 60,
                 noise_echo_threshold: float = 0.3,
                 shadow_echo_threshold: float = 0.6,
                 shadow_min_duration: int = 20,
                 entropy_spike_threshold: float = 0.15,
                 trauma_rate_threshold: float = 0.05):
        self.echo_buffer: deque = deque(maxlen=buffer_size)
        self.psi_echo_index: float = 0.0
        self.confidence: float = 0.0
        self._current_class = DestabilizationClass.STABLE
        self._perturbation_start: Optional[int] = None
        self._samples_since_perturbation: int = 0

        # Thresholds
        self._noise_echo_threshold = noise_echo_threshold
        self._shadow_echo_threshold = shadow_echo_threshold
        self._shadow_min_duration = shadow_min_duration
        self._entropy_spike_threshold = entropy_spike_threshold
        self._trauma_rate_threshold = trauma_rate_threshold

        # Baseline tracking
        self._baseline_ccs: float = 0.5
        self._baseline_count: int = 0

    def classify(self, state: MultiWaveCoherenceState) -> DestabilizationClass:
        ccs = state.scalar_coherence
        self.echo_buffer.append(ccs)

        # Update baseline from healthy readings
        if ccs > 0.5 and self._current_class == DestabilizationClass.STABLE:
            alpha = 0.05
            self._baseline_ccs = alpha * ccs + (1 - alpha) * self._baseline_ccs
            self._baseline_count += 1

        # Need minimum history
        if len(self.echo_buffer) < 10:
            self._current_class = DestabilizationClass.STABLE
            self.confidence = 0.0
            return self._current_class

        # Compute psi_echo_index (autocorrelation at lags 5-20)
        self._compute_psi_echo_index()

        # Compute entropy rate (variance of recent CCS)
        recent = list(self.echo_buffer)
        entropy = np.std(recent[-10:]) if len(recent) >= 10 else 0.0

        # Detect perturbation
        deviation = abs(ccs - self._baseline_ccs)
        is_perturbed = deviation > self._entropy_spike_threshold

        if is_perturbed:
            if self._perturbation_start is None:
                self._perturbation_start = len(self.echo_buffer)
            self._samples_since_perturbation = 0
        else:
            self._samples_since_perturbation += 1
            if self._samples_since_perturbation > 3:
                self._perturbation_start = None

        # Check for trauma indicators
        hr_stable = state.breath_entrained
        fast_idx = 3  # FAST band
        core_idx = 2  # CORE band
        fast_spike = state.band_amplitudes[fast_idx] > 0.7
        core_collapse = state.band_amplitudes[core_idx] < 0.3

        # Compute entropy rate of change
        if len(recent) >= 5:
            entropy_recent = [np.std(recent[max(0, i-3):i+1]) for i in range(len(recent)-5, len(recent))]
            entropy_rate = (entropy_recent[-1] - entropy_recent[0]) / max(len(entropy_recent), 1)
        else:
            entropy_rate = 0.0

        # Classification logic
        if not is_perturbed and self._perturbation_start is None:
            self._current_class = DestabilizationClass.STABLE
            self.confidence = 1.0 - entropy

        elif (not hr_stable or fast_spike or core_collapse) and entropy_rate > self._trauma_rate_threshold:
            self._current_class = DestabilizationClass.TRAUMA
            self.confidence = min(0.95, 0.6 + entropy_rate * 5)

        elif self.psi_echo_index > self._shadow_echo_threshold and is_perturbed:
            perturbation_duration = (len(self.echo_buffer) - self._perturbation_start
                                     if self._perturbation_start else 0)
            if perturbation_duration >= self._shadow_min_duration:
                self._current_class = DestabilizationClass.SHADOW
                self.confidence = min(0.95, self.psi_echo_index)
            else:
                self._current_class = DestabilizationClass.STABLE
                self.confidence = 0.5

        elif self.psi_echo_index < self._noise_echo_threshold and self._samples_since_perturbation > 0:
            self._current_class = DestabilizationClass.NOISE
            self.confidence = min(0.95, 1.0 - self.psi_echo_index)

        else:
            # Ambiguous — keep previous or default to stable
            if not is_perturbed:
                self._current_class = DestabilizationClass.STABLE
                self.confidence = 0.5

        return self._current_class

    def _compute_psi_echo_index(self) -> None:
        """Compute autocorrelation of CCS values at lags 5-20."""
        values = np.array(self.echo_buffer)
        n = len(values)
        if n < 21:
            self.psi_echo_index = 0.0
            return

        mean = np.mean(values)
        var = np.var(values)
        if var < 1e-10:
            self.psi_echo_index = 0.0
            return

        autocorrs = []
        for lag in range(5, min(21, n)):
            c = np.mean((values[:n-lag] - mean) * (values[lag:] - mean)) / var
            autocorrs.append(abs(c))

        self.psi_echo_index = float(np.mean(autocorrs)) if autocorrs else 0.0

    def get_status(self) -> Dict[str, Any]:
        return {
            'classification': self._current_class.value,
            'psi_echo_index': round(self.psi_echo_index, 4),
            'confidence': round(self.confidence, 4),
            'baseline_ccs': round(self._baseline_ccs, 4),
            'buffer_length': len(self.echo_buffer),
        }

    def reset(self) -> None:
        self.echo_buffer.clear()
        self.psi_echo_index = 0.0
        self.confidence = 0.0
        self._current_class = DestabilizationClass.STABLE
        self._perturbation_start = None
        self._samples_since_perturbation = 0
        self._baseline_ccs = 0.5
        self._baseline_count = 0
```

**Step 4: Run tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_scouter.py -v`
Expected: All 6 tests PASS

**Step 5: Commit**

```bash
git add extensions/coherence-glove/coherence/scouter.py extensions/coherence-glove/tests/test_scouter.py
git commit -m "feat: add SCOUTER 3-class destabilization classifier (noise/shadow/trauma)"
```

---

## Task 6: ArcSession — Multi-Session Arc Tracking

**Files:**
- Modify: `extensions/coherence-glove/coherence/session.py`
- Create: `extensions/coherence-glove/tests/test_arc.py`

**Step 1: Write failing tests**

```python
# tests/test_arc.py
"""Tests for multi-session arc tracking."""
import pytest
import json
from datetime import datetime, timedelta
from coherence.session import (
    CoherenceSession,
    SessionManager,
    ArcSession,
    ArcMetrics,
)


class TestArcSession:
    def test_create_arc(self):
        arc = ArcSession.create(arc_length=9, name="shadow integration")
        assert arc.arc_length == 9
        assert arc.completed_sessions == 0
        assert arc.arc_status == 'active'
        assert arc.arc_name == "shadow integration"

    def test_add_session(self):
        arc = ArcSession.create(arc_length=3)
        session = CoherenceSession.create()
        session.record_ccs(0.6)
        session.end()
        arc.add_session(session)
        assert arc.completed_sessions == 1
        assert len(arc.session_ids) == 1
        assert arc.metrics.ccs_trend == [0.6]

    def test_auto_complete(self):
        arc = ArcSession.create(arc_length=2)
        for _ in range(2):
            s = CoherenceSession.create()
            s.record_ccs(0.5)
            s.end()
            arc.add_session(s)
        assert arc.arc_status == 'complete'

    def test_bloom_suppressed_before_session_3(self):
        arc = ArcSession.create(arc_length=9)
        assert arc.should_suppress_bloom()
        s = CoherenceSession.create(); s.end(); arc.add_session(s)
        assert arc.should_suppress_bloom()
        s = CoherenceSession.create(); s.end(); arc.add_session(s)
        assert arc.should_suppress_bloom()
        s = CoherenceSession.create(); s.end(); arc.add_session(s)
        assert not arc.should_suppress_bloom()

    def test_progressive_ccs_threshold(self):
        arc = ArcSession.create(arc_length=9)
        base = arc.ccs_threshold_for_session(0)
        assert arc.ccs_threshold_for_session(1) == pytest.approx(base + 0.05)
        assert arc.ccs_threshold_for_session(4) == pytest.approx(base + 0.20)

    def test_to_dict_roundtrip(self):
        arc = ArcSession.create(arc_length=5, name="test")
        s = CoherenceSession.create(); s.record_ccs(0.7); s.end()
        arc.add_session(s)
        d = arc.to_dict()
        restored = ArcSession.from_dict(d)
        assert restored.arc_id == arc.arc_id
        assert restored.completed_sessions == 1


class TestSessionManagerArcs:
    def test_start_and_get_arc(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        arc = mgr.start_arc(arc_length=5, name="test arc")
        assert mgr.active_arc is not None
        assert arc.arc_length == 5

    def test_session_auto_attaches_to_arc(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        mgr.start_arc(arc_length=5)
        mgr.start_session()
        mgr.record_ccs(0.6)
        mgr.end_session()
        assert mgr.active_arc.completed_sessions == 1

    def test_arc_persists(self, tmp_path):
        mgr = SessionManager(sessions_dir=str(tmp_path))
        mgr.start_arc(arc_length=3, name="persist test")
        mgr.start_session()
        mgr.record_ccs(0.5)
        mgr.end_session()
        # Check arcs.json written
        arcs_file = tmp_path / 'arcs.json'
        assert arcs_file.exists()
```

**Step 2: Run to verify failure**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_arc.py -v`
Expected: FAIL

**Step 3: Add ArcSession and ArcMetrics to session.py**

Append to `coherence/session.py`:

```python
@dataclass
class ArcMetrics:
    avg_ccs: float = 0.0
    ccs_trend: List[float] = field(default_factory=list)
    entropy_trend: List[float] = field(default_factory=list)
    rtc_trend: List[float] = field(default_factory=list)
    subjective_trend: List[float] = field(default_factory=list)
    model_mismatch_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
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
        return cls(**d)


@dataclass
class ArcSession:
    arc_id: str
    arc_name: Optional[str]
    arc_length: int
    completed_sessions: int
    session_ids: List[str]
    metrics: ArcMetrics
    arc_status: str  # 'active' | 'complete' | 'interrupted'
    created_at: datetime
    updated_at: datetime
    _ccs_threshold_step: float = 0.05
    _ccs_baseline: float = 0.3

    @classmethod
    def create(cls, arc_length: int, name: Optional[str] = None) -> 'ArcSession':
        now = datetime.now()
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
        self.session_ids.append(session.session_id)
        self.completed_sessions += 1
        self.updated_at = datetime.now()

        # Update metrics
        if session.coherence_history:
            avg_ccs = sum(session.coherence_history) / len(session.coherence_history)
            self.metrics.ccs_trend.append(round(avg_ccs, 4))
            entropy = float(max(session.coherence_history) - min(session.coherence_history))
            self.metrics.entropy_trend.append(round(entropy, 4))
        else:
            self.metrics.ccs_trend.append(session.final_ccs)
            self.metrics.entropy_trend.append(0.0)

        if session.subjective_score is not None:
            self.metrics.subjective_trend.append(session.subjective_score)

        if session.model_confidence < 0.5:
            self.metrics.model_mismatch_count += 1

        # Recompute avg_ccs
        if self.metrics.ccs_trend:
            self.metrics.avg_ccs = sum(self.metrics.ccs_trend) / len(self.metrics.ccs_trend)

        # Auto-complete
        if self.completed_sessions >= self.arc_length:
            self.arc_status = 'complete'

    def should_suppress_bloom(self) -> bool:
        return self.completed_sessions < 3

    def ccs_threshold_for_session(self, session_index: int) -> float:
        return self._ccs_baseline + self._ccs_threshold_step * session_index

    def to_dict(self) -> Dict[str, Any]:
        return {
            'arc_id': self.arc_id,
            'arc_name': self.arc_name,
            'arc_length': self.arc_length,
            'completed_sessions': self.completed_sessions,
            'session_ids': self.session_ids,
            'metrics': self.metrics.to_dict(),
            'arc_status': self.arc_status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'ArcSession':
        return cls(
            arc_id=d['arc_id'],
            arc_name=d.get('arc_name'),
            arc_length=d['arc_length'],
            completed_sessions=d['completed_sessions'],
            session_ids=d['session_ids'],
            metrics=ArcMetrics.from_dict(d['metrics']),
            arc_status=d['arc_status'],
            created_at=datetime.fromisoformat(d['created_at']),
            updated_at=datetime.fromisoformat(d['updated_at']),
        )
```

Also add arc support to `SessionManager`:

```python
# Add to SessionManager.__init__:
    self._active_arc: Optional[ArcSession] = None

# Add properties and methods:
    @property
    def active_arc(self) -> Optional[ArcSession]:
        return self._active_arc

    def start_arc(self, arc_length: int, name: Optional[str] = None) -> ArcSession:
        if self._active_arc and self._active_arc.arc_status == 'active':
            self._active_arc.arc_status = 'interrupted'
            self._persist_arcs()
        arc = ArcSession.create(arc_length=arc_length, name=name)
        self._active_arc = arc
        self._persist_arcs()
        return arc

    def end_arc(self) -> Optional[ArcSession]:
        if self._active_arc is None:
            return None
        self._active_arc.arc_status = 'complete'
        self._active_arc.updated_at = datetime.now()
        self._persist_arcs()
        arc = self._active_arc
        self._active_arc = None
        return arc

    def get_arc_status(self) -> Dict[str, Any]:
        if self._active_arc is None:
            return {'active': False}
        return {
            'active': True,
            **self._active_arc.to_dict(),
        }

    def _persist_arcs(self) -> None:
        arcs_file = os.path.join(self._sessions_dir, 'arcs.json')
        arcs_data = []
        if os.path.exists(arcs_file):
            try:
                with open(arcs_file) as f:
                    arcs_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                arcs_data = []
        if self._active_arc:
            # Update or append
            found = False
            for i, a in enumerate(arcs_data):
                if a.get('arc_id') == self._active_arc.arc_id:
                    arcs_data[i] = self._active_arc.to_dict()
                    found = True
                    break
            if not found:
                arcs_data.append(self._active_arc.to_dict())
        with open(arcs_file, 'w') as f:
            json.dump(arcs_data, f, indent=2)

# Modify end_session to attach to arc:
    def end_session(self) -> Optional[CoherenceSession]:
        if self._active_session is None:
            return None
        session = self._active_session
        session.end()
        self._persist_session(session)
        # Attach to active arc
        if self._active_arc and self._active_arc.arc_status == 'active':
            self._active_arc.add_session(session)
            self._persist_arcs()
        self._active_session = None
        if self._on_session_end:
            self._on_session_end(session)
        return session
```

**Step 4: Run tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_arc.py tests/test_session.py -v`
Expected: All tests PASS

**Step 5: Commit**

```bash
git add extensions/coherence-glove/coherence/session.py extensions/coherence-glove/tests/test_arc.py
git commit -m "feat: add ArcSession multi-session arc tracking with bloom suppression"
```

---

## Task 7: Kuramoto Network Coupling

**Files:**
- Create: `extensions/coherence-glove/coherence/network.py`
- Create: `extensions/coherence-glove/tests/test_network.py`

**Step 1: Write failing tests**

```python
# tests/test_network.py
"""Tests for Kuramoto network phase coupling."""
import pytest
import math
from coherence.network import NetworkNode, KuramotoNetwork


class TestNetworkNode:
    def test_create_node(self):
        node = NetworkNode(node_id='a', phase=0.0, natural_freq=0.1, ccs=0.5)
        assert node.node_id == 'a'

    def test_ccs_readonly_in_coupling(self):
        """CCS is stored but never used in phase coupling math."""
        node = NetworkNode(node_id='a', phase=0.0, natural_freq=0.1, ccs=0.5)
        node.ccs = 0.9  # Can be updated
        assert node.ccs == 0.9  # But it's informational only


class TestKuramotoNetwork:
    def test_empty_network(self):
        net = KuramotoNetwork(coupling_strength=0.5)
        net.step(0.1)  # Should not crash

    def test_single_node_free_runs(self):
        net = KuramotoNetwork(coupling_strength=0.5)
        node = NetworkNode(node_id='a', phase=0.0, natural_freq=1.0, ccs=0.5)
        net.add_node(node)
        net.step(0.1)
        # Phase should advance by natural_freq * dt
        assert net.nodes['a'].phase == pytest.approx(0.1, abs=0.01)

    def test_two_nodes_synchronize(self):
        """Two nodes with different phases should converge over time."""
        net = KuramotoNetwork(coupling_strength=2.0)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        net.add_node(NetworkNode('b', phase=math.pi, natural_freq=1.0, ccs=0.5))

        initial_diff = abs(net.nodes['a'].phase - net.nodes['b'].phase)

        for _ in range(100):
            net.step(0.05)

        final_diff = abs(net.nodes['a'].phase - net.nodes['b'].phase) % (2 * math.pi)
        # With same natural freq and strong coupling, should synchronize
        assert final_diff < initial_diff or final_diff > (2 * math.pi - 0.5)

    def test_phase_lock_score(self):
        net = KuramotoNetwork(coupling_strength=1.0)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        net.add_node(NetworkNode('b', phase=0.01, natural_freq=1.0, ccs=0.5))
        # Nearly identical phases = high phase lock
        assert net.phase_lock_score() > 0.9

    def test_ccs_never_coupled(self):
        """Verify CCS values don't affect phase dynamics."""
        net1 = KuramotoNetwork(coupling_strength=1.0)
        net1.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.1))
        net1.add_node(NetworkNode('b', phase=1.0, natural_freq=1.0, ccs=0.1))

        net2 = KuramotoNetwork(coupling_strength=1.0)
        net2.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.9))
        net2.add_node(NetworkNode('b', phase=1.0, natural_freq=1.0, ccs=0.9))

        for _ in range(10):
            net1.step(0.1)
            net2.step(0.1)

        assert net1.nodes['a'].phase == pytest.approx(net2.nodes['a'].phase, abs=1e-10)

    def test_get_status(self):
        net = KuramotoNetwork(coupling_strength=1.0)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        status = net.get_status()
        assert status['node_count'] == 1
        assert 'phase_lock_score' in status
```

**Step 2: Run to verify failure**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_network.py -v`
Expected: FAIL

**Step 3: Implement**

```python
# coherence/network.py
"""
Kuramoto Network Phase Coupling.

2-node prototype for multi-user coherence synchronization.
Uses Kuramoto model: dphi_i/dt = omega_i + (K/N) * SUM sin(phi_j - phi_i)

CRITICAL RULE: Couple phase ONLY, never CCS directly.
CCS is stored for informational purposes but never enters coupling math.

(c) 2026 Anywave Creations
MIT License
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class NetworkNode:
    node_id: str
    phase: float          # breath phase (radians)
    natural_freq: float   # omega_i (rad/s)
    ccs: float            # read-only — NEVER coupled


class KuramotoNetwork:
    """Kuramoto oscillator network for phase synchronization."""

    def __init__(self, coupling_strength: float = 0.5):
        self.nodes: Dict[str, NetworkNode] = {}
        self.coupling_strength = coupling_strength

    def add_node(self, node: NetworkNode) -> None:
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        self.nodes.pop(node_id, None)

    def step(self, dt: float) -> None:
        if len(self.nodes) == 0:
            return

        n = len(self.nodes)
        node_list = list(self.nodes.values())

        # Compute phase updates (all at once, then apply)
        updates = {}
        for node in node_list:
            phase_coupling = 0.0
            for other in node_list:
                if other.node_id != node.node_id:
                    phase_coupling += math.sin(other.phase - node.phase)

            dphi = node.natural_freq + (self.coupling_strength / n) * phase_coupling
            updates[node.node_id] = node.phase + dt * dphi

        # Apply updates
        for node_id, new_phase in updates.items():
            self.nodes[node_id].phase = new_phase

    def phase_lock_score(self) -> float:
        """Compute order parameter r = |1/N * SUM exp(i*phi_k)|.

        r=1 means perfect synchronization, r=0 means no coherence.
        """
        if len(self.nodes) < 2:
            return 1.0

        n = len(self.nodes)
        real_sum = sum(math.cos(node.phase) for node in self.nodes.values())
        imag_sum = sum(math.sin(node.phase) for node in self.nodes.values())

        r = math.sqrt(real_sum**2 + imag_sum**2) / n
        return r

    def get_status(self) -> Dict[str, Any]:
        return {
            'node_count': len(self.nodes),
            'coupling_strength': self.coupling_strength,
            'phase_lock_score': round(self.phase_lock_score(), 4),
            'nodes': {
                nid: {
                    'phase': round(n.phase, 4),
                    'natural_freq': round(n.natural_freq, 4),
                    'ccs': round(n.ccs, 4),
                }
                for nid, n in self.nodes.items()
            },
        }

    def reset(self) -> None:
        self.nodes.clear()
```

**Step 4: Run tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/test_network.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
git add extensions/coherence-glove/coherence/network.py extensions/coherence-glove/tests/test_network.py
git commit -m "feat: add Kuramoto network phase coupling (2-node prototype)"
```

---

## Task 8: Update coherence/__init__.py

**Files:**
- Modify: `extensions/coherence-glove/coherence/__init__.py`

**Step 1: Add new module exports**

Add these imports and exports to `__init__.py`:

```python
from .session import (
    SessionPhase,
    CoherenceSession,
    SessionManager,
    ArcSession,
    ArcMetrics,
)

from .subjective import (
    SubjectiveEntry,
    SubjectiveTracker,
)

from .scouter import (
    DestabilizationClass,
    Scouter,
)

from .network import (
    NetworkNode,
    KuramotoNetwork,
)
```

Add to `__all__`:
```python
    # Session
    'SessionPhase',
    'CoherenceSession',
    'SessionManager',
    'ArcSession',
    'ArcMetrics',
    # Subjective
    'SubjectiveEntry',
    'SubjectiveTracker',
    # SCOUTER
    'DestabilizationClass',
    'Scouter',
    # Network
    'NetworkNode',
    'KuramotoNetwork',
```

**Step 2: Run all tests**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
git add extensions/coherence-glove/coherence/__init__.py
git commit -m "feat: export session, subjective, scouter, network from coherence package"
```

---

## Task 9: Wire New MCP Tools into mcp_server.py

**Files:**
- Modify: `extensions/coherence-glove/mcp_server.py`

**Step 1: Add tool definitions to TOOLS list**

Add 11 new tool definitions after the existing 8 tools (after line 187):

```python
    # --- Session Intelligence tools ---
    {
        'name': 'coherence_session_start',
        'description': 'Start a new coherence session. Auto-ends any active session. Returns session_id.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_session_end',
        'description': 'End the active coherence session. Persists session data and triggers end-of-session hooks.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_session_status',
        'description': 'Get current session status: phase (dissolve/process/reconstitute), prompt count, CCS trend, model confidence.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_push_subjective',
        'description': 'Record user subjective coherence score (0-10). Computes divergence from measured CCS.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'score': {
                    'type': 'number',
                    'description': 'Subjective coherence score 0-10.',
                    'minimum': 0,
                    'maximum': 10,
                },
                'source': {
                    'type': 'string',
                    'enum': ['mid_session', 'end_session'],
                    'description': 'When score was captured.',
                },
            },
            'required': ['score', 'source'],
        },
    },
    {
        'name': 'coherence_get_scouter_class',
        'description': 'Get current SCOUTER destabilization classification: stable, noise (Class A), shadow (Class B), or trauma (Class C).',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_arc_start',
        'description': 'Start a multi-session arc for long-horizon coherence tracking. Bloom suppressed until session 3.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'arc_length': {
                    'type': 'integer',
                    'description': 'Target number of sessions in arc (e.g. 9).',
                    'minimum': 2,
                },
                'name': {
                    'type': 'string',
                    'description': 'Optional name for the arc.',
                },
            },
            'required': ['arc_length'],
        },
    },
    {
        'name': 'coherence_arc_status',
        'description': 'Get current arc status: completed sessions, CCS/entropy trends, bloom suppression state.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_arc_end',
        'description': 'Manually end the active arc.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
    {
        'name': 'coherence_network_join',
        'description': 'Register this instance as a node in the Kuramoto phase coupling network.',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'node_id': {
                    'type': 'string',
                    'description': 'Unique node identifier.',
                },
                'natural_freq': {
                    'type': 'number',
                    'description': 'Natural oscillation frequency (rad/s). Defaults to breath rate.',
                },
            },
            'required': ['node_id'],
        },
    },
    {
        'name': 'coherence_network_status',
        'description': 'Get network phase coupling status: connected nodes, phase lock score.',
        'inputSchema': {
            'type': 'object',
            'properties': {},
        },
    },
```

**Step 2: Add component instances to CoherenceGloveServer.__init__**

After line 222 (`log.info('Engine initialized...')`), add:

```python
        # Session Intelligence components
        from coherence.session import SessionManager
        from coherence.subjective import SubjectiveTracker
        from coherence.scouter import Scouter
        from coherence.network import KuramotoNetwork, NetworkNode

        self.session_mgr = SessionManager()
        self.subjective = SubjectiveTracker()
        self.scouter = Scouter()
        self.network = KuramotoNetwork()
```

**Step 3: Add tool handlers to _handle_tools_call**

After the `coherence_reset` handler (around line 376), add:

```python
            elif tool_name == 'coherence_session_start':
                result = self._session_start()
            elif tool_name == 'coherence_session_end':
                result = self._session_end()
            elif tool_name == 'coherence_session_status':
                result = self.session_mgr.get_status()
            elif tool_name == 'coherence_push_subjective':
                result = self._push_subjective(
                    arguments.get('score', 5.0),
                    arguments.get('source', 'mid_session'),
                )
            elif tool_name == 'coherence_get_scouter_class':
                result = self.scouter.get_status()
            elif tool_name == 'coherence_arc_start':
                result = self._arc_start(
                    arguments.get('arc_length', 9),
                    arguments.get('name'),
                )
            elif tool_name == 'coherence_arc_status':
                result = self.session_mgr.get_arc_status()
            elif tool_name == 'coherence_arc_end':
                result = self._arc_end()
            elif tool_name == 'coherence_network_join':
                result = self._network_join(
                    arguments.get('node_id', ''),
                    arguments.get('natural_freq'),
                )
            elif tool_name == 'coherence_network_status':
                result = self.network.get_status()
```

**Step 4: Add handler methods to CoherenceGloveServer**

```python
    def _session_start(self) -> Dict:
        session = self.session_mgr.start_session()
        self.subjective.reset_session()
        log.info(f'Session started: {session.session_id}')
        return {'session_id': session.session_id, 'phase': session.phase.value}

    def _session_end(self) -> Dict:
        session = self.session_mgr.end_session()
        if session is None:
            return {'error': 'No active session'}
        log.info(f'Session ended: {session.session_id}')
        return session.to_dict()

    def _push_subjective(self, score: float, source: str) -> Dict:
        session = self.session_mgr.active_session
        if session is None:
            return {'error': 'No active session'}
        with self._lock:
            ccs = self.engine.get_current_state()
            ccs_val = ccs.scalar_coherence if ccs else 0.0
        entry = self.subjective.record(session.session_id, score, source, ccs_val)
        session.subjective_score = score
        session.model_confidence = self.subjective.model_confidence()
        return entry.to_dict()

    def _arc_start(self, arc_length: int, name: Optional[str] = None) -> Dict:
        arc = self.session_mgr.start_arc(arc_length, name)
        log.info(f'Arc started: {arc.arc_id} (length={arc_length})')
        return arc.to_dict()

    def _arc_end(self) -> Dict:
        arc = self.session_mgr.end_arc()
        if arc is None:
            return {'error': 'No active arc'}
        return arc.to_dict()

    def _network_join(self, node_id: str, natural_freq: Optional[float] = None) -> Dict:
        if not node_id:
            return {'error': 'node_id is required'}
        freq = natural_freq or 0.1  # Default ~6 BPM breath rate
        from coherence.network import NetworkNode
        node = NetworkNode(node_id=node_id, phase=0.0, natural_freq=freq, ccs=0.0)
        self.network.add_node(node)
        log.info(f'Network node joined: {node_id}')
        return self.network.get_status()
```

**Step 5: Wire SCOUTER into state updates and session prompt tracking into push_text**

In `_push_text` method, after `self.engine.process_window()`, add:

```python
        # Record prompt in session
        self.session_mgr.record_prompt(token_count=len(text.split()) * 2)  # rough token estimate

        # Update SCOUTER and session CCS
        with self._lock:
            current = self.engine.get_current_state()
            if current:
                self.scouter.classify(current)
                phase_change = self.session_mgr.record_ccs(current.scalar_coherence)
                # Log scouter events to session
                if (self.scouter._current_class.value != 'stable' and
                        self.session_mgr.active_session):
                    self.session_mgr.active_session.scouter_events.append(
                        self.scouter.get_status()
                    )
```

**Step 6: Run full test suite**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 7: Commit**

```bash
git add extensions/coherence-glove/mcp_server.py
git commit -m "feat: wire 11 new MCP tools for session intelligence"
```

---

## Task 10: Frontend — SubjectivePrompt Component

**Files:**
- Create: `web-app/src/components/SubjectivePrompt.tsx`
- Modify: `web-app/src/hooks/useCoherenceGlove.ts`

**Step 1: Create SubjectivePrompt component**

```tsx
// web-app/src/components/SubjectivePrompt.tsx
import { useState } from 'react'
import { callTool } from '@/services/mcp'
import { useCoherenceGlove } from '@/hooks/useCoherenceGlove'

interface SubjectivePromptProps {
  source: 'mid_session' | 'end_session'
  onDismiss: () => void
}

export function SubjectivePrompt({ source, onDismiss }: SubjectivePromptProps) {
  const [score, setScore] = useState(5)
  const [submitting, setSubmitting] = useState(false)

  const label = source === 'mid_session'
    ? 'How coherent do you feel right now?'
    : 'How did that session feel overall?'

  const handleSubmit = async () => {
    setSubmitting(true)
    try {
      await callTool({
        toolName: 'coherence_push_subjective',
        arguments: { score, source },
      })
    } catch {
      // Silent — non-critical
    } finally {
      setSubmitting(false)
      onDismiss()
    }
  }

  return (
    <div className="fixed bottom-16 left-1/2 -translate-x-1/2 z-50 bg-zinc-900 border border-zinc-700 rounded-lg p-4 shadow-lg w-80">
      <p className="text-sm text-zinc-300 mb-3">{label}</p>
      <div className="flex items-center gap-3">
        <span className="text-xs text-zinc-500">0</span>
        <input
          type="range"
          min={0}
          max={10}
          step={1}
          value={score}
          onChange={(e) => setScore(Number(e.target.value))}
          className="flex-1 accent-violet-500"
        />
        <span className="text-xs text-zinc-500">10</span>
        <span className="text-sm font-mono text-violet-400 w-6 text-center">{score}</span>
      </div>
      <div className="flex justify-end gap-2 mt-3">
        <button
          onClick={onDismiss}
          className="text-xs text-zinc-500 hover:text-zinc-300 px-2 py-1"
        >
          Skip
        </button>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="text-xs bg-violet-600 hover:bg-violet-500 text-white px-3 py-1 rounded disabled:opacity-50"
        >
          {submitting ? '...' : 'Submit'}
        </button>
      </div>
    </div>
  )
}
```

**Step 2: Add session tracking to useCoherenceGlove**

Add to the `CoherenceGloveState` interface:

```typescript
  // Session state
  sessionActive: boolean
  sessionPhase: string
  promptCount: number
  tokenEstimate: number
  showSubjectivePrompt: boolean
  subjectivePromptSource: 'mid_session' | 'end_session'
```

Add defaults to the store:

```typescript
  sessionActive: false,
  sessionPhase: 'dissolve',
  promptCount: 0,
  tokenEstimate: 0,
  showSubjectivePrompt: false,
  subjectivePromptSource: 'mid_session' as const,
```

Add session actions:

```typescript
  startSession: async () => {
    try {
      await callTool({ toolName: 'coherence_session_start', arguments: {} })
      set({ sessionActive: true, sessionPhase: 'dissolve', promptCount: 0, tokenEstimate: 0 })
    } catch { /* silent */ }
  },

  endSession: async () => {
    try {
      await callTool({ toolName: 'coherence_session_end', arguments: {} })
      set({ sessionActive: false, showSubjectivePrompt: true, subjectivePromptSource: 'end_session' })
    } catch { /* silent */ }
  },

  dismissSubjectivePrompt: () => {
    set({ showSubjectivePrompt: false })
  },
```

Modify `pushText` to track prompts and trigger mid-session prompt:

```typescript
  // After successful push, increment prompt count
  const newPromptCount = get().promptCount + 1
  const newTokenEstimate = get().tokenEstimate + text.split(/\s+/).length * 2
  const updates: Partial<CoherenceGloveState> = {
    promptCount: newPromptCount,
    tokenEstimate: newTokenEstimate,
  }

  // Check mid-session prompt trigger
  const settings = JSON.parse(localStorage.getItem('coherenceGloveSettings') || '{}')
  const minPrompts = settings.midSessionMinPrompts ?? 3
  const minTokens = settings.midSessionMinTokens ?? 1000
  const enableMid = settings.enableMidSessionPrompt ?? true

  if (enableMid && newPromptCount >= minPrompts && newTokenEstimate >= minTokens && !get().showSubjectivePrompt) {
    updates.showSubjectivePrompt = true
    updates.subjectivePromptSource = 'mid_session'
  }

  set(updates)
```

**Step 3: Commit**

```bash
git add web-app/src/components/SubjectivePrompt.tsx web-app/src/hooks/useCoherenceGlove.ts
git commit -m "feat: add SubjectivePrompt component and session tracking in frontend"
```

---

## Task 11: Integration Test + Final Verification

**Files:**
- Create: `extensions/coherence-glove/tests/test_integration.py`

**Step 1: Write integration test**

```python
# tests/test_integration.py
"""Integration tests — full session lifecycle with all components."""
import pytest
import numpy as np
from datetime import datetime
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
            mgr.end_session()

            if i < 3:
                assert arc.should_suppress_bloom()
            else:
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
```

**Step 2: Run full test suite**

Run: `cd C:/ANYWAVEREPO/jan-ai-fork/extensions/coherence-glove && python -m pytest tests/ -v`
Expected: All tests PASS across all test files

**Step 3: Commit**

```bash
git add extensions/coherence-glove/tests/test_integration.py
git commit -m "test: add integration tests for full session intelligence lifecycle"
```

---

## Task 12: Final Commit — Update CLAUDE.md + Docs

**Files:**
- Modify: `C:/Users/abc/CLAUDE.md`
- Modify: `C:/Users/abc/.claude/FP_WORK_STATE.json`

**Step 1: Update CLAUDE.md IMMEDIATE CONTEXT**

Update the IMMEDIATE CONTEXT section with the new features implemented.

**Step 2: Update FP_WORK_STATE.json**

Add the new features to the `coherenceGlove` section:
- `sessionIntelligence: "IMPLEMENTED — session lifecycle, SCOUTER, subjective scores, arc tracking, Kuramoto network"`

**Step 3: Final commit**

```bash
cd C:/ANYWAVEREPO/jan-ai-fork
git add -A extensions/coherence-glove/
git status
git log --oneline -10
```

Verify all commits are clean and no files are missing.

---

## Summary

| Task | Description | New Files | Tests |
|------|-------------|-----------|-------|
| 1 | Test infrastructure | conftest.py | - |
| 2 | Session data model | session.py | 7 |
| 3 | SessionManager | - | 6 |
| 4 | Subjective score | subjective.py | 7 |
| 5 | SCOUTER classifier | scouter.py | 6 |
| 6 | ArcSession | session.py (extend) | 9 |
| 7 | Kuramoto network | network.py | 7 |
| 8 | Package exports | __init__.py | - |
| 9 | MCP tool wiring | mcp_server.py | - |
| 10 | Frontend component | SubjectivePrompt.tsx | - |
| 11 | Integration tests | test_integration.py | 4 |
| 12 | State file updates | CLAUDE.md | - |

**Total: 12 tasks, 4 new Python modules, 1 new React component, ~46 tests, 11 new MCP tools**
