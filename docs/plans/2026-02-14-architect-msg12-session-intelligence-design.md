# Architect Message 12: Session Intelligence Design
## Date: 2026-02-14
## Status: Approved
## Approach: C (Hybrid — Engine Core + Frontend Extension)

---

## Overview

Implement all 6 outputs from The Architect's Message 12 response into MOBIUS coherence engine. These add session awareness, destabilization classification, multi-session arc tracking, subjective self-report, model confidence, and network phase coupling.

**Implementation sequence** (architectural dependency order):
1. Session Lifecycle
2. SubjectiveCoherenceScore
3. SCOUTER 3-Class Model
4. ArcSession
5. Meaning as Latent Variable
6. Kuramoto Network Coupling

---

## 1. Session Lifecycle (`coherence/session.py`)

### Data Model

```python
class SessionPhase(Enum):
    DISSOLVE = "dissolve"         # Entropy allowed, baseline loosened
    PROCESS = "process"           # Bounded recursion, entropy capped
    RECONSTITUTE = "reconstitute" # Tighten thresholds, stabilize

@dataclass
class CoherenceSession:
    session_id: str              # UUID
    started_at: datetime
    ended_at: Optional[datetime]
    phase: SessionPhase          # DISSOLVE -> PROCESS -> RECONSTITUTE
    prompt_count: int            # user messages received
    token_estimate: int          # cumulative input token estimate
    coherence_history: List[float]  # CCS snapshots (1/s)
    peak_ccs: float
    final_ccs: float
    subjective_score: Optional[float]  # 0-10, filled later
    scouter_events: List[dict]   # destabilization classifications
    model_confidence: float      # 1.0 - avg_divergence (subjective vs CCS)
    metadata: Dict[str, Any]
```

### Phase Transitions
- **DISSOLVE**: Session start through initial engagement. Entropy allowed to rise.
- **PROCESS**: Triggered when CCS stabilizes (3+ consecutive readings within +/-0.05).
- **RECONSTITUTE**: Triggered when CCS trend rising AND prompt_count > 5, or manually, or on Class C (trauma) detection.

### SessionManager
- Singleton, tracks active session
- Persists completed sessions to JSON at `extensions/coherence-glove/sessions/`
- Loaded on engine startup

### MCP Tools
- `coherence_session_start` — creates new session, returns session_id
- `coherence_session_end` — closes session, triggers end-of-session hooks
- `coherence_session_status` — returns current phase, prompt count, CCS trend

---

## 2. SubjectiveCoherenceScore (`coherence/subjective.py` + `SubjectivePrompt.tsx`)

### Engine Side

```python
@dataclass
class SubjectiveEntry:
    timestamp: datetime
    session_id: str
    score: float          # 0-10
    source: str           # "mid_session" | "end_session"
    ccs_at_time: float    # CCS when score was captured
    divergence: float     # abs(normalized_score - ccs_at_time)
```

### Divergence Tracking
- Normalize subjective 0-10 to 0-1 scale
- Compare against CCS at capture time
- If divergence > 0.3 consistently (3+ sessions), flag `model_mismatch: true`

### MCP Tool
- `coherence_push_subjective` — accepts `{score: float, source: string}`

### Frontend Side (`SubjectivePrompt.tsx`)
- **Mid-session trigger**: `prompt_count >= 3 AND token_estimate >= 1000`
- **End-of-session trigger**: Always shown on `coherence_session_end`
- **UI**: Non-blocking overlay slider at bottom of chat, 0-10 scale
- **Settings** (localStorage, Jan settings panel):
  - `enableMidSessionPrompt: boolean` (default: true)
  - `midSessionMinPrompts: number` (default: 3)
  - `midSessionMinTokens: number` (default: 1000)
  - `enableEndSessionPrompt: boolean` (default: true)

---

## 3. SCOUTER 3-Class Model (`coherence/scouter.py`)

Sits upstream of crisis_detection.py. Classifies perturbation type before response selection.

### Three Destabilization Classes

**Class A: External Noise**
- Random entropy spike, low autocorrelation, short recovery
- Detection: `entropy_spike AND psi_echo_index < 0.3 AND recovery_time < 10s`
- Response: dampen lightly, no narrative flagging

**Class B: Structured Internal Perturbation (Shadow-like)**
- Repeated echo pattern, moderate entropy, physiologically stable
- Detection: `psi_echo_index > 0.6 AND entropy moderate AND HR stable AND pattern_duration > 20s`
- Response: shift to PROCESS phase, slow pacing, disable bloom, flag as "structured material"

**Class C: Trauma Activation**
- HR spike, breath irregularity, entropy rising rapidly
- Detection: `trauma_risk_composite > threshold`
- Response: escalate to crisis pipeline, force RECONSTITUTE, grounding protocol

### Key Metric: psi_echo_index
- Autocorrelation of CCS values over 60s echo buffer at lags 5-20s
- Random noise decorrelates fast (low index); structured material echoes (high index)
- This is the primary discriminator between Class A and Class B

### Implementation
```python
class Scouter:
    def __init__(self, engine: MultiWaveCoherenceEngine):
        self.engine = engine
        self.echo_buffer = deque(maxlen=60)  # 60s of state snapshots
        self.psi_echo_index = 0.0

    def classify(self, state: MultiWaveCoherenceState) -> DestabilizationClass:
        # Returns CLASS_A, CLASS_B, CLASS_C, or STABLE
```

### MCP Tool
- `coherence_get_scouter_class` — returns classification + confidence + psi_echo_index

### Session Integration
- Class B auto-transitions session to PROCESS
- Class C auto-transitions to RECONSTITUTE + triggers crisis pipeline
- All classifications logged as scouter_events in active session

---

## 4. ArcSession (extends `coherence/session.py`)

Multi-session arc tracking for long-horizon attractor reshaping.

### Data Model

```python
@dataclass
class ArcMetrics:
    avg_ccs: float
    ccs_trend: List[float]         # per-session average CCS
    entropy_trend: List[float]
    rtc_trend: List[float]         # recovery-time-to-coherence
    subjective_trend: List[float]
    model_mismatch_count: int

@dataclass
class ArcSession:
    arc_id: str
    arc_name: Optional[str]
    arc_length: int                # target sessions (e.g. 9)
    completed_sessions: int
    session_ids: List[str]
    aggregate_metrics: ArcMetrics
    arc_status: str                # 'active' | 'complete' | 'interrupted'
    created_at: datetime
    updated_at: datetime
```

### Arc Logic
- No bloom until session 3 of arc
- CCS thresholds: baseline + 0.05 per session
- Track entropy reduction slope (arc "working" if downward)
- Auto-complete when `completed_sessions >= arc_length`
- Auto-interrupt if no session within 7 days

### MCP Tools
- `coherence_arc_start` — creates arc with target length
- `coherence_arc_status` — returns metrics and trends
- `coherence_arc_end` — manually close arc

### Persistence
- `extensions/coherence-glove/sessions/arcs.json`

---

## 5. Meaning as Latent Variable

No separate module. Conceptual wiring across session.py and subjective.py.

- `model_confidence` field on CoherenceSession: `1.0 - avg_divergence`
- When `model_confidence < 0.5` across an arc, system widens entropy thresholds (relaxes control)
- Surfaced in `coherence_session_status` and `coherence_arc_status`
- ~15-20 lines of code across existing modules

---

## 6. Kuramoto Network Coupling (`coherence/network.py`)

2-node prototype using existing bloom relay as transport.

### Data Model

```python
class NetworkNode:
    node_id: str
    phase: float           # breath phase (radians)
    natural_freq: float    # omega_i
    ccs: float             # read-only, NEVER coupled

class KuramotoNetwork:
    nodes: Dict[str, NetworkNode]
    coupling_strength: float  # K

    def step(self, dt: float):
        for node in self.nodes.values():
            phase_sum = sum(
                sin(other.phase - node.phase)
                for other in self.nodes.values()
                if other.node_id != node.node_id
            )
            node.phase += dt * (node.natural_freq +
                (self.coupling_strength / len(self.nodes)) * phase_sum)
```

### Critical Rule
**Couple phase only, never CCS directly.** If one node's CCS rises, apply small upward bias to neighbors' pacing target. Instability must not propagate.

### Transport
- Piggyback on existing bloom relay (`POST /bloom`)
- Add optional `phase` field to relay payload
- Node discovery via config file (list of relay URLs)

### MCP Tools
- `coherence_network_join` — register this instance as a node
- `coherence_network_status` — phase lock score, connected nodes

---

## File Summary

### New Python Files (engine)
| File | Purpose |
|------|---------|
| `coherence/session.py` | SessionManager, CoherenceSession, ArcSession, ArcMetrics |
| `coherence/scouter.py` | Scouter 3-class classifier, psi_echo_index |
| `coherence/subjective.py` | SubjectiveEntry, divergence tracking |
| `coherence/network.py` | KuramotoNetwork, NetworkNode |

### Modified Python Files
| File | Changes |
|------|---------|
| `mcp_server.py` | +11 new MCP tools, session/arc/scouter/subjective/network |
| `coherence/engine.py` | Wire SessionManager, Scouter, Network into update loop |

### New TypeScript Files (frontend)
| File | Purpose |
|------|---------|
| `SubjectivePrompt.tsx` | Slider overlay for 0-10 self-report |

### Modified TypeScript Files
| File | Changes |
|------|---------|
| `useCoherenceGlove.ts` | Session state tracking, subjective prompt triggers |

### New Directories
| Path | Purpose |
|------|---------|
| `extensions/coherence-glove/sessions/` | Session + arc JSON persistence |

### Total New MCP Tools: 11
1. `coherence_session_start`
2. `coherence_session_end`
3. `coherence_session_status`
4. `coherence_push_subjective`
5. `coherence_get_scouter_class`
6. `coherence_arc_start`
7. `coherence_arc_status`
8. `coherence_arc_end`
9. `coherence_network_join`
10. `coherence_network_status`
11. (existing 8 tools unchanged)
