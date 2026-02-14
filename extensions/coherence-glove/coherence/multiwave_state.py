"""
Multi-Wave Coherence State representation.

Central data structure for coherence analysis output, integrating
band decomposition, breath intentionality, and BTF inference results.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from datetime import datetime
import json
import numpy as np

# Import φ-constants
try:
    from ra_constants import PHI_BANDS, PHI_WEIGHTS, PHI, PHI_INVERSE
except ImportError:
    PHI = 1.618033988749895
    PHI_INVERSE = 0.6180339887498949

    def phi_power(n: int) -> float:
        if n == 0:
            return 1.0
        elif n > 0:
            return PHI ** n
        else:
            return (1.0 / PHI) ** (-n)

    PHI_BANDS = {
        'ULTRA': phi_power(-2),
        'SLOW': phi_power(-1),
        'CORE': phi_power(0),
        'FAST': phi_power(1),
        'RAPID': phi_power(2),
    }

    PHI_WEIGHTS = {
        'ULTRA': phi_power(-2),
        'SLOW': phi_power(-1),
        'CORE': phi_power(0),
        'FAST': phi_power(-1),
        'RAPID': phi_power(-2),
    }

# Band order for array indexing
BAND_ORDER = ['ULTRA', 'SLOW', 'CORE', 'FAST', 'RAPID']


@dataclass
class MultiWaveCoherenceState:
    """Complete multi-wave coherence state at a point in time.

    This is the primary output of the coherence analysis pipeline,
    containing all information needed for consent state determination.

    Attributes:
        timestamp: When this state was computed
        band_amplitudes: Amplitude per φ-band [ULTRA, SLOW, CORE, FAST, RAPID]
        band_phases: Phase (radians) per φ-band
        signal_coherences: Per-signal coherence scores (e.g., {'hrv': 0.7, 'breath': 0.9})
        intentionality: Breath-derived intentionality score 0-1
        breath_entrained: Whether breath is entrained to φ-target
        breath_rate_hz: Current breath rate in Hz
        scalar_coherence: Final scalar coherence value 0-1
        uncertainty: Confidence interval / uncertainty estimate
        reference_phase: Phase reference (typically breath if intentional)
        btf_factors: Optional BTF spatial/temporal factors
    """
    timestamp: datetime
    band_amplitudes: np.ndarray  # Shape: (5,)
    band_phases: np.ndarray  # Shape: (5,)
    signal_coherences: Dict[str, float]
    intentionality: float
    breath_entrained: bool
    breath_rate_hz: float
    scalar_coherence: float
    uncertainty: float
    reference_phase: float = 0.0
    btf_factors: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate array shapes."""
        if not isinstance(self.band_amplitudes, np.ndarray):
            self.band_amplitudes = np.array(self.band_amplitudes, dtype=np.float64)
        if not isinstance(self.band_phases, np.ndarray):
            self.band_phases = np.array(self.band_phases, dtype=np.float64)

        assert len(self.band_amplitudes) == 5, "Must have 5 band amplitudes"
        assert len(self.band_phases) == 5, "Must have 5 band phases"

        # Clamp values to valid ranges
        self.intentionality = max(0.0, min(1.0, self.intentionality))
        self.scalar_coherence = max(0.0, min(1.0, self.scalar_coherence))
        self.uncertainty = max(0.0, min(1.0, self.uncertainty))

    @property
    def amplitude_dict(self) -> Dict[str, float]:
        """Get amplitudes as dict with band names."""
        return {name: float(self.band_amplitudes[i]) for i, name in enumerate(BAND_ORDER)}

    @property
    def phase_dict(self) -> Dict[str, float]:
        """Get phases as dict with band names."""
        return {name: float(self.band_phases[i]) for i, name in enumerate(BAND_ORDER)}

    @property
    def dominant_band(self) -> str:
        """Get name of band with highest amplitude."""
        return BAND_ORDER[int(np.argmax(self.band_amplitudes))]

    @property
    def weighted_amplitude(self) -> float:
        """Compute φ-weighted sum of amplitudes."""
        weights = np.array([PHI_WEIGHTS[name] for name in BAND_ORDER])
        return float(np.dot(weights, self.band_amplitudes))

    @property
    def phase_alignment(self) -> float:
        """Compute how well phases are aligned to reference.

        Returns mean cos(phase - reference), ranging -1 to 1.
        """
        phase_diffs = self.band_phases - self.reference_phase
        return float(np.mean(np.cos(phase_diffs)))

    @property
    def confidence(self) -> float:
        """Inverse of uncertainty for convenience."""
        return 1.0 - self.uncertainty

    def to_acsp_input(self) -> Dict[str, Any]:
        """Convert to ACSP consent state input format.

        Returns dict compatible with ACSP consent determination:
        - coherence: scalar value for threshold comparison
        - intentionality: breath-derived control indicator
        - uncertainty: confidence bounds
        - metadata: supporting information

        Consent thresholds (from ra-constants):
        - >= 1.0: FULL_CONSENT
        - >= φ^-1 (0.618): DIMINISHED
        - >= φ^-2 (0.382): SUSPENDED
        - < φ^-2: EMERGENCY
        """
        return {
            'coherence': self.scalar_coherence,
            'intentionality': self.intentionality,
            'uncertainty': self.uncertainty,
            'breath_entrained': self.breath_entrained,
            'timestamp': self.timestamp.isoformat(),
            'metadata': {
                'dominant_band': self.dominant_band,
                'weighted_amplitude': self.weighted_amplitude,
                'phase_alignment': self.phase_alignment,
                'breath_rate_hz': self.breath_rate_hz,
                'signal_coherences': self.signal_coherences,
            }
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full serialization to dictionary."""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'band_amplitudes': self.band_amplitudes.tolist(),
            'band_phases': self.band_phases.tolist(),
            'signal_coherences': self.signal_coherences,
            'intentionality': self.intentionality,
            'breath_entrained': self.breath_entrained,
            'breath_rate_hz': self.breath_rate_hz,
            'scalar_coherence': self.scalar_coherence,
            'uncertainty': self.uncertainty,
            'reference_phase': self.reference_phase,
            # Computed properties
            'dominant_band': self.dominant_band,
            'weighted_amplitude': self.weighted_amplitude,
            'phase_alignment': self.phase_alignment,
            'confidence': self.confidence,
        }

        if self.btf_factors is not None:
            # Serialize BTF factors (convert numpy arrays if present)
            btf_serialized = {}
            for key, value in self.btf_factors.items():
                if isinstance(value, np.ndarray):
                    btf_serialized[key] = value.tolist()
                else:
                    btf_serialized[key] = value
            result['btf_factors'] = btf_serialized

        return result

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> 'MultiWaveCoherenceState':
        """Deserialize from dictionary."""
        return cls(
            timestamp=datetime.fromisoformat(d['timestamp']),
            band_amplitudes=np.array(d['band_amplitudes']),
            band_phases=np.array(d['band_phases']),
            signal_coherences=d['signal_coherences'],
            intentionality=d['intentionality'],
            breath_entrained=d['breath_entrained'],
            breath_rate_hz=d['breath_rate_hz'],
            scalar_coherence=d['scalar_coherence'],
            uncertainty=d['uncertainty'],
            reference_phase=d.get('reference_phase', 0.0),
            btf_factors=d.get('btf_factors'),
        )

    @classmethod
    def from_json(cls, json_str: str) -> 'MultiWaveCoherenceState':
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def create_default(cls, timestamp: Optional[datetime] = None) -> 'MultiWaveCoherenceState':
        """Create a default/neutral state.

        Useful for initialization before first measurements arrive.
        """
        return cls(
            timestamp=timestamp or datetime.now(),
            band_amplitudes=np.zeros(5),
            band_phases=np.zeros(5),
            signal_coherences={},
            intentionality=0.0,
            breath_entrained=False,
            breath_rate_hz=0.0,
            scalar_coherence=0.0,
            uncertainty=1.0,  # Maximum uncertainty
            reference_phase=0.0,
        )


def compute_scalar_coherence(band_amplitudes: np.ndarray,
                              band_phases: np.ndarray,
                              reference_phase: float,
                              intentionality: float,
                              intentionality_threshold: float = 0.5) -> float:
    """Compute scalar coherence from band data.

    Formula: C = I * sum(w_k * A_k * cos(psi_k - psi_ref))

    When intentionality > threshold, breath phase is used as reference.
    Otherwise, CORE band phase is used.

    Args:
        band_amplitudes: Array of 5 band amplitudes
        band_phases: Array of 5 band phases (radians)
        reference_phase: Reference phase (typically breath)
        intentionality: Intentionality score 0-1
        intentionality_threshold: Threshold for intentional control

    Returns:
        Scalar coherence value 0-1
    """
    # Get weights
    weights = np.array([PHI_WEIGHTS[name] for name in BAND_ORDER])

    # Phase alignment term
    phase_diffs = band_phases - reference_phase
    alignment = np.cos(phase_diffs)

    # Weighted sum
    weighted_sum = np.dot(weights, band_amplitudes * alignment)

    # Normalize by weight sum
    weight_sum = np.sum(weights)
    if weight_sum > 0:
        weighted_sum /= weight_sum

    # Apply intentionality factor
    if intentionality > intentionality_threshold:
        coherence = intentionality * weighted_sum
    else:
        # Reduced coherence without intentional control
        coherence = 0.5 * weighted_sum

    # Clamp to [0, 1]
    return float(max(0.0, min(1.0, coherence)))
