"""
Scalar coherence reduction from multi-wave band data.

Implements the formula: C = I * sum(w_k * A_k * cos(psi_k - psi_ref))

When intentionality > threshold, breath phase serves as reference.
Otherwise, CORE band phase is used as a stable reference.

(c) 2026 Anywave Creations
MIT License
"""

from typing import Optional, Dict
import numpy as np

# Import φ-constants
try:
    from ra_constants import PHI_WEIGHTS, PHI, PHI_INVERSE
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

    PHI_WEIGHTS = {
        'ULTRA': phi_power(-2),
        'SLOW': phi_power(-1),
        'CORE': phi_power(0),
        'FAST': phi_power(-1),
        'RAPID': phi_power(-2),
    }

# Band order for array indexing
BAND_ORDER = ['ULTRA', 'SLOW', 'CORE', 'FAST', 'RAPID']
CORE_INDEX = 2  # Index of CORE band


def get_phi_weights() -> np.ndarray:
    """Get φ-scaled weights as numpy array in band order."""
    return np.array([PHI_WEIGHTS[name] for name in BAND_ORDER])


def compute_phase_coherence(band_phases: np.ndarray,
                             reference_phase: float) -> float:
    """Compute phase coherence (alignment) across bands.

    Args:
        band_phases: Array of 5 band phases (radians)
        reference_phase: Reference phase (radians)

    Returns:
        Phase coherence in range [-1, 1]
    """
    phase_diffs = band_phases - reference_phase
    # Weighted mean of cos(phase_diff)
    weights = get_phi_weights()
    alignment = np.cos(phase_diffs)
    return float(np.sum(weights * alignment) / np.sum(weights))


def compute_amplitude_factor(band_amplitudes: np.ndarray) -> float:
    """Compute weighted amplitude factor.

    Args:
        band_amplitudes: Array of 5 band amplitudes

    Returns:
        Weighted amplitude sum (can exceed 1.0)
    """
    weights = get_phi_weights()
    return float(np.sum(weights * band_amplitudes) / np.sum(weights))


def select_reference_phase(band_phases: np.ndarray,
                           breath_phase: Optional[float],
                           intentionality: float,
                           intentionality_threshold: float = 0.5) -> float:
    """Select appropriate reference phase based on intentionality.

    When user is intentionally controlling breath, use breath phase.
    Otherwise, use CORE band phase as stable reference.

    Args:
        band_phases: Array of 5 band phases
        breath_phase: Breath signal phase if available
        intentionality: Current intentionality score
        intentionality_threshold: Threshold for intentional control

    Returns:
        Selected reference phase
    """
    if intentionality > intentionality_threshold and breath_phase is not None:
        return breath_phase
    else:
        # Fall back to CORE band phase
        return band_phases[CORE_INDEX]


def compute_scalar_coherence(band_amplitudes: np.ndarray,
                              band_phases: np.ndarray,
                              intentionality: float,
                              breath_phase: Optional[float] = None,
                              intentionality_threshold: float = 0.5,
                              reference_phase: Optional[float] = None) -> float:
    """Compute scalar coherence from band data.

    Formula: C = I * sum(w_k * A_k * cos(psi_k - psi_ref)) / sum(w_k)

    When intentionality > threshold, breath phase is used as reference,
    enabling intentional control over coherence. Otherwise, CORE band
    phase provides a stable autonomous reference.

    Args:
        band_amplitudes: Array of 5 band amplitudes [ULTRA..RAPID]
        band_phases: Array of 5 band phases (radians)
        intentionality: Intentionality score 0-1
        breath_phase: Optional breath signal phase
        intentionality_threshold: Threshold for intentional mode
        reference_phase: Override reference phase (skips selection)

    Returns:
        Scalar coherence value clamped to [0, 1]
    """
    # Select reference phase
    if reference_phase is None:
        ref_phase = select_reference_phase(
            band_phases, breath_phase, intentionality, intentionality_threshold
        )
    else:
        ref_phase = reference_phase

    # Get weights
    weights = get_phi_weights()

    # Phase alignment term: cos(psi_k - psi_ref)
    phase_diffs = band_phases - ref_phase
    alignment = np.cos(phase_diffs)

    # Weighted sum: sum(w_k * A_k * cos(psi_k - psi_ref))
    weighted_sum = np.sum(weights * band_amplitudes * alignment)

    # Normalize by weight sum
    weight_sum = np.sum(weights)
    normalized = weighted_sum / weight_sum if weight_sum > 0 else 0.0

    # Apply intentionality factor
    if intentionality > intentionality_threshold:
        # Full intentional mode
        coherence = intentionality * normalized
    else:
        # Reduced coherence without intentional control
        # Scale by 0.5 to indicate autonomous (not volitional) coherence
        coherence = 0.5 * normalized

    # Clamp to valid range
    return float(max(0.0, min(1.0, coherence)))


def coherence_to_consent_level(coherence: float,
                                intentionality: float) -> str:
    """Map coherence to consent level name.

    Thresholds (from φ-scaling):
    - >= 1.0: FULL_CONSENT (theoretical max)
    - >= φ^-1 (0.618): FULL_CONSENT (practical)
    - >= φ^-2 (0.382): DIMINISHED
    - >= φ^-3 (0.236): SUSPENDED
    - < φ^-3: EMERGENCY

    Intentionality factors into transitions.

    Args:
        coherence: Scalar coherence value
        intentionality: Intentionality score

    Returns:
        Consent level name string
    """
    PHI_NEG1 = PHI_INVERSE  # 0.618
    PHI_NEG2 = PHI_INVERSE ** 2  # 0.382
    PHI_NEG3 = PHI_INVERSE ** 3  # 0.236

    # Adjust thresholds based on intentionality
    # Low intentionality raises thresholds (harder to achieve full consent)
    intent_factor = 0.9 + 0.1 * intentionality  # 0.9 to 1.0

    if coherence >= PHI_NEG1 * intent_factor:
        return 'FULL_CONSENT'
    elif coherence >= PHI_NEG2 * intent_factor:
        return 'DIMINISHED'
    elif coherence >= PHI_NEG3 * intent_factor:
        return 'SUSPENDED'
    else:
        return 'EMERGENCY'


def compute_uncertainty(band_amplitudes: np.ndarray,
                        signal_qualities: Optional[Dict[str, float]] = None) -> float:
    """Estimate uncertainty in coherence measurement.

    Higher uncertainty when:
    - Band amplitudes are low (weak signals)
    - Signal quality is poor
    - Bands have high variance

    Args:
        band_amplitudes: Array of 5 band amplitudes
        signal_qualities: Optional dict of signal quality scores

    Returns:
        Uncertainty value 0-1 (1 = maximum uncertainty)
    """
    # Base uncertainty from amplitude strength
    mean_amp = np.mean(band_amplitudes)
    amp_uncertainty = max(0.0, 1.0 - mean_amp)

    # Variance in amplitudes increases uncertainty
    amp_variance = np.var(band_amplitudes)
    variance_uncertainty = min(1.0, amp_variance * 2.0)

    # Signal quality factor
    if signal_qualities:
        mean_quality = np.mean(list(signal_qualities.values()))
        quality_uncertainty = 1.0 - mean_quality
    else:
        quality_uncertainty = 0.5  # Unknown quality

    # Combined uncertainty
    uncertainty = (amp_uncertainty + variance_uncertainty + quality_uncertainty) / 3.0

    return float(max(0.0, min(1.0, uncertainty)))
