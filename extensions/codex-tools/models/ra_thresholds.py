"""
RA-derived thresholds for the Codex Field Pipeline.

All thresholds derive from the five core Ra constants:
  PHI (φ)   = 1.618...    Golden ratio — coherence attractor
  E         = 2.718...    Euler's number — decay/smoothing
  √10       = 3.162...    Dimensional collapse timing
  α⁻¹       = 137.036... Fine-structure constant inverse — binding
  ANKH (𝔄)  = 5.089...    Master harmonic

Canonical source: rpp-spec/rpp/ra_constants.py (v2.2.0-RaCanonical)

Threshold tier system (0-1 field scores):
  Tier 0: BINDING_THRESHOLD  (0.203) — bare minimum to hold coherence
  Tier 1: RADEL_ALPHA        (0.368) — smoothing/incubation readiness
  Tier 2: COMPLEMENT_PHI     (0.382) — diminished but functional
  Tier 3: PHI_NORM           (0.618) — full coherence alignment
"""

# ── Core Ra Constants ───────────────────────────────────────────────

PHI: float = 1.6180339887498948482
"""Golden Ratio (φ). Governs coherence thresholds and harmonic scaling."""

E: float = 2.718281828459045
"""Euler's number (e). Governs RADEL smoothing and decay patterns."""

ALPHA_INVERSE: float = 137.035999084
"""Fine-structure constant inverse (α⁻¹ ≈ 137). Binding threshold."""

ANKH: float = 5.08938
"""Ankh constant (𝔄). Master harmonic for coherence completion weight."""


# ── Normalized Thresholds ───────────────────────────────────────────

PHI_NORM: float = PHI - 1.0
"""φ - 1 ≈ 0.618. The golden ratio attractor in [0,1] space."""

COMPLEMENT_PHI: float = 1.0 - PHI_NORM
"""1 - (φ-1) ≈ 0.382. Diminished coherence boundary."""

BINDING_THRESHOLD: float = 137.0 / 674.0
"""α⁻¹ / MAX_COHERENCE ≈ 0.203. Below this, field fragments."""

RADEL_ALPHA: float = 1.0 / E
"""1/e ≈ 0.368. Smoothing coefficient / incubation readiness."""


# ── Scaled Thresholds ──────────────────────────────────────────────

PHI_SQUARED: float = PHI * PHI
"""φ² ≈ 2.618. Sigma accumulation cap (replaces hardcoded 2.0)."""

RESONANCE_SIGMA_CODEX: float = 0.88
"""From Codex spec: Σᵣ ≥ 0.88 for coherence union. Not RA-derived."""


# ── Operator-Specific Thresholds ────────────────────────────────────

# VECTIS: minimum coherence for directional lock
VECTIS_LOCK: float = BINDING_THRESHOLD
"""0.203 — the minimum binding coefficient to lock trajectory."""

# CALYPSO: minimum sigma for incubation
CALYPSO_INCUBATION: float = RADEL_ALPHA
"""0.368 — smoothing threshold for incubation readiness."""

# MORPHIS: coherence floor for structural reorganization
MORPHIS_COHERENCE: float = COMPLEMENT_PHI
"""0.382 — diminished boundary sufficient for restructuring."""

# LIMITA: threshold governor
LIMITA_TRIGGER: float = 1.0 - BINDING_THRESHOLD
"""0.797 — within one binding unit of capacity, governor engages."""

LIMITA_GOVERNOR: float = PHI_NORM + BINDING_THRESHOLD
"""0.821 — governor reduces sigma to this fraction of capacity."""

# LUXIS: ego inflation prevention
LUXIS_EGO_TRIGGER: float = LIMITA_TRIGGER
"""0.797 — radiance above this risks ego inflation."""

LUXIS_EGO_CAP: float = LIMITA_GOVERNOR
"""0.821 — governed radiance level."""

# SYNTARA: alignment bonus per HARMONIA layer
SYNTARA_ALIGNMENT_BONUS: float = COMPLEMENT_PHI / 4.0
"""~0.096 per aligned layer. Full alignment adds one COMPLEMENT_PHI."""

# HARMONIA: multi-layer alignment thresholds
HARMONIA_BREATH: float = PHI_NORM
"""0.618 — breath symmetry must reach golden attractor."""

HARMONIA_EMOTION_MAX: float = PHI_NORM
"""0.618 — emotional charge above this is too volatile for alignment."""

HARMONIA_LOGIC: float = COMPLEMENT_PHI
"""0.382 — coherence minimum for logic alignment."""

HARMONIA_SOMATIC_BREATH: float = COMPLEMENT_PHI
"""0.382 — breath minimum for somatic grounding."""

HARMONIA_SOMATIC_COHERENCE: float = BINDING_THRESHOLD
"""0.203 — coherence minimum for somatic grounding."""

# AURORA: pattern emergence
AURORA_HIGH_COHERENCE: float = PHI_NORM
"""0.618 — coherence level indicating high-quality field state."""

# ARCHON: encoding quality
ARCHON_WISDOM: float = PHI_NORM
"""0.618 — above this, event encodes as wisdom (not just experience)."""
