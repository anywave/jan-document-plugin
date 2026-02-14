"""
Phi-band signal decomposition for multi-wave coherence analysis.

Decomposes biometric signals into five φ-scaled frequency bands
using bandpass filtering and Hilbert transform for amplitude/phase extraction.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np
from scipy import signal as scipy_signal
from scipy.signal import hilbert

# Import φ-constants from ra-constants
try:
    from ra_constants import (
        PHI_BANDS,
        PHI_OMEGA,
        PHI_WEIGHTS,
        PhiBand,
        band_frequency_range,
        PHI,
    )
except ImportError:
    # Fallback if ra-constants not installed - define locally
    PHI = 1.618033988749895

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

    PHI_OMEGA = {k: 2 * np.pi * v for k, v in PHI_BANDS.items()}

    PHI_WEIGHTS = {
        'ULTRA': phi_power(-2),
        'SLOW': phi_power(-1),
        'CORE': phi_power(0),
        'FAST': phi_power(-1),
        'RAPID': phi_power(-2),
    }

# Band names in order from lowest to highest frequency
BAND_ORDER = ['ULTRA', 'SLOW', 'CORE', 'FAST', 'RAPID']

# Band indices
BAND_INDEX = {name: i for i, name in enumerate(BAND_ORDER)}


@dataclass
class BandDecomposition:
    """Result of φ-band decomposition for a signal.

    Attributes:
        amplitudes: Array of 5 amplitudes, one per band [ULTRA, SLOW, CORE, FAST, RAPID]
        phases: Array of 5 phases in radians
        powers: Array of 5 band powers (amplitude squared)
        band_signals: Dict mapping band name to filtered signal array
        sample_rate: Original signal sample rate
        timestamp: Optional timestamp for this decomposition
    """
    amplitudes: np.ndarray  # Shape: (5,)
    phases: np.ndarray  # Shape: (5,)
    powers: np.ndarray  # Shape: (5,)
    band_signals: Dict[str, np.ndarray] = field(default_factory=dict)
    sample_rate: float = 0.0
    timestamp: Optional[float] = None

    def __post_init__(self):
        """Validate array shapes."""
        assert len(self.amplitudes) == 5, "Must have 5 band amplitudes"
        assert len(self.phases) == 5, "Must have 5 band phases"
        assert len(self.powers) == 5, "Must have 5 band powers"

    @property
    def amplitude_dict(self) -> Dict[str, float]:
        """Get amplitudes as dict with band names."""
        return {name: float(self.amplitudes[i]) for i, name in enumerate(BAND_ORDER)}

    @property
    def phase_dict(self) -> Dict[str, float]:
        """Get phases as dict with band names."""
        return {name: float(self.phases[i]) for i, name in enumerate(BAND_ORDER)}

    @property
    def power_dict(self) -> Dict[str, float]:
        """Get powers as dict with band names."""
        return {name: float(self.powers[i]) for i, name in enumerate(BAND_ORDER)}

    @property
    def dominant_band(self) -> str:
        """Get name of band with highest power."""
        return BAND_ORDER[int(np.argmax(self.powers))]

    @property
    def weighted_coherence(self) -> float:
        """Compute φ-weighted coherence from this decomposition.

        Uses formula: C = Σ_k w_k × A_k (ignoring phase for simple metric)
        """
        weights = np.array([PHI_WEIGHTS[name] for name in BAND_ORDER])
        return float(np.dot(weights, self.amplitudes))

    def to_dict(self) -> Dict:
        """Serialize to dictionary."""
        return {
            'amplitudes': self.amplitude_dict,
            'phases': self.phase_dict,
            'powers': self.power_dict,
            'dominant_band': self.dominant_band,
            'weighted_coherence': self.weighted_coherence,
            'sample_rate': self.sample_rate,
            'timestamp': self.timestamp
        }


def get_band_frequency_range(band_name: str) -> Tuple[float, float]:
    """Get frequency range for a φ band.

    Uses geometric mean boundaries: (φ^(k-0.5), φ^(k+0.5))

    Args:
        band_name: One of ULTRA, SLOW, CORE, FAST, RAPID

    Returns:
        (lower_hz, upper_hz) tuple
    """
    center_freq = PHI_BANDS[band_name]
    phi_sqrt = np.sqrt(PHI)
    lower = center_freq / phi_sqrt
    upper = center_freq * phi_sqrt
    return (lower, upper)


def design_bandpass_filter(low_hz: float,
                           high_hz: float,
                           sample_rate: float,
                           order: int = 4) -> Tuple[np.ndarray, np.ndarray]:
    """Design a Butterworth bandpass filter.

    Args:
        low_hz: Lower cutoff frequency in Hz
        high_hz: Upper cutoff frequency in Hz
        sample_rate: Sample rate in Hz
        order: Filter order (default 4)

    Returns:
        (b, a) filter coefficients
    """
    nyquist = sample_rate / 2.0

    # Clamp frequencies to valid range
    low_norm = max(0.001, low_hz / nyquist)
    high_norm = min(0.999, high_hz / nyquist)

    # Handle edge case where band is above Nyquist
    if low_norm >= 0.999:
        low_norm = 0.99
        high_norm = 0.999

    if low_norm >= high_norm:
        high_norm = low_norm + 0.001

    try:
        b, a = scipy_signal.butter(order, [low_norm, high_norm], btype='band')
    except ValueError:
        # Fallback to simple lowpass if bandpass fails
        b, a = scipy_signal.butter(order, high_norm, btype='low')

    return b, a


def bandpass_filter(data: np.ndarray,
                    low_hz: float,
                    high_hz: float,
                    sample_rate: float,
                    order: int = 4) -> np.ndarray:
    """Apply bandpass filter to signal.

    Args:
        data: Input signal array
        low_hz: Lower cutoff frequency
        high_hz: Upper cutoff frequency
        sample_rate: Sample rate in Hz
        order: Filter order

    Returns:
        Filtered signal
    """
    if len(data) < 12:  # Need minimum samples for filtering
        return np.zeros_like(data)

    b, a = design_bandpass_filter(low_hz, high_hz, sample_rate, order)

    # Use filtfilt for zero-phase filtering
    try:
        filtered = scipy_signal.filtfilt(b, a, data, padlen=min(len(data) - 1, 3 * max(len(b), len(a))))
    except ValueError:
        # Fallback if filtfilt fails
        filtered = scipy_signal.lfilter(b, a, data)

    return filtered


def extract_instantaneous_amplitude_phase(signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Extract instantaneous amplitude and phase using Hilbert transform.

    Args:
        signal: Input signal array

    Returns:
        (amplitude, phase) arrays
    """
    if len(signal) == 0:
        return np.array([0.0]), np.array([0.0])

    # Apply Hilbert transform to get analytic signal
    analytic = hilbert(signal)

    # Instantaneous amplitude = magnitude of analytic signal
    amplitude = np.abs(analytic)

    # Instantaneous phase = angle of analytic signal
    phase = np.angle(analytic)

    return amplitude, phase


def decompose_signal(data: np.ndarray,
                     sample_rate: float,
                     quality_mask: Optional[np.ndarray] = None,
                     filter_order: int = 4) -> BandDecomposition:
    """Decompose a signal into five φ-scaled frequency bands.

    Args:
        data: Input signal array
        sample_rate: Sample rate in Hz
        quality_mask: Optional boolean mask (True = valid sample)
        filter_order: Butterworth filter order

    Returns:
        BandDecomposition with amplitudes, phases, powers per band
    """
    # Apply quality mask if provided
    if quality_mask is not None:
        # Replace invalid samples with interpolated values
        valid_indices = np.where(quality_mask)[0]
        if len(valid_indices) > 1:
            data = np.interp(
                np.arange(len(data)),
                valid_indices,
                data[valid_indices]
            )

    # Detrend and normalize
    data = data - np.mean(data)
    std = np.std(data)
    if std > 1e-10:
        data = data / std

    # Initialize output arrays
    amplitudes = np.zeros(5)
    phases = np.zeros(5)
    powers = np.zeros(5)
    band_signals = {}

    # Nyquist frequency
    nyquist = sample_rate / 2.0

    for i, band_name in enumerate(BAND_ORDER):
        low_hz, high_hz = get_band_frequency_range(band_name)

        # Check if band is within Nyquist limit
        if low_hz >= nyquist:
            # Band is above Nyquist - cannot extract
            band_signals[band_name] = np.zeros_like(data)
            continue

        # Clamp high frequency to Nyquist
        high_hz = min(high_hz, nyquist * 0.95)

        # Apply bandpass filter
        filtered = bandpass_filter(data, low_hz, high_hz, sample_rate, filter_order)
        band_signals[band_name] = filtered

        # Extract amplitude and phase via Hilbert transform
        amp, phase = extract_instantaneous_amplitude_phase(filtered)

        # Store mean amplitude, current phase (last sample), and power
        amplitudes[i] = np.mean(amp)
        phases[i] = phase[-1] if len(phase) > 0 else 0.0
        powers[i] = np.mean(amp ** 2)

    return BandDecomposition(
        amplitudes=amplitudes,
        phases=phases,
        powers=powers,
        band_signals=band_signals,
        sample_rate=sample_rate
    )


class BandDecomposer:
    """Stateful band decomposer for streaming signals.

    Maintains filter state for continuous processing.
    """

    def __init__(self, sample_rate: float, filter_order: int = 4):
        """Initialize decomposer.

        Args:
            sample_rate: Expected sample rate of input signals
            filter_order: Butterworth filter order
        """
        self.sample_rate = sample_rate
        self.filter_order = filter_order

        # Pre-compute filter coefficients for each band
        self._filters: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}
        self._filter_states: Dict[str, np.ndarray] = {}

        nyquist = sample_rate / 2.0

        for band_name in BAND_ORDER:
            low_hz, high_hz = get_band_frequency_range(band_name)

            if low_hz < nyquist:
                high_hz = min(high_hz, nyquist * 0.95)
                b, a = design_bandpass_filter(low_hz, high_hz, sample_rate, filter_order)
                self._filters[band_name] = (b, a)
                # Initialize filter state
                self._filter_states[band_name] = scipy_signal.lfilter_zi(b, a) * 0

    def process(self,
                data: np.ndarray,
                quality_mask: Optional[np.ndarray] = None) -> BandDecomposition:
        """Process a chunk of signal data.

        Maintains filter state between calls for streaming operation.

        Args:
            data: Input signal chunk
            quality_mask: Optional quality mask

        Returns:
            BandDecomposition for this chunk
        """
        # Apply quality mask
        if quality_mask is not None:
            valid_indices = np.where(quality_mask)[0]
            if len(valid_indices) > 1:
                data = np.interp(
                    np.arange(len(data)),
                    valid_indices,
                    data[valid_indices]
                )

        # Detrend
        data = data - np.mean(data)

        amplitudes = np.zeros(5)
        phases = np.zeros(5)
        powers = np.zeros(5)
        band_signals = {}

        for i, band_name in enumerate(BAND_ORDER):
            if band_name not in self._filters:
                band_signals[band_name] = np.zeros_like(data)
                continue

            b, a = self._filters[band_name]
            zi = self._filter_states[band_name]

            # Apply filter with state preservation
            filtered, self._filter_states[band_name] = scipy_signal.lfilter(
                b, a, data, zi=zi * data[0] if len(data) > 0 else zi
            )

            band_signals[band_name] = filtered

            # Extract amplitude and phase
            amp, phase = extract_instantaneous_amplitude_phase(filtered)
            amplitudes[i] = np.mean(amp)
            phases[i] = phase[-1] if len(phase) > 0 else 0.0
            powers[i] = np.mean(amp ** 2)

        return BandDecomposition(
            amplitudes=amplitudes,
            phases=phases,
            powers=powers,
            band_signals=band_signals,
            sample_rate=self.sample_rate
        )

    def reset(self) -> None:
        """Reset filter states for new signal stream."""
        for band_name in self._filter_states:
            b, a = self._filters[band_name]
            self._filter_states[band_name] = scipy_signal.lfilter_zi(b, a) * 0


def decompose_multi_stream(streams: Dict[str, Tuple[np.ndarray, float]],
                           target_rate: Optional[float] = None) -> Dict[str, BandDecomposition]:
    """Decompose multiple signal streams into φ bands.

    Handles variable sample rates by resampling to common rate.

    Args:
        streams: Dict mapping stream name to (data, sample_rate) tuple
        target_rate: Target sample rate (uses max if not specified)

    Returns:
        Dict mapping stream name to BandDecomposition
    """
    if not streams:
        return {}

    # Determine target sample rate
    if target_rate is None:
        target_rate = max(sr for _, sr in streams.values())

    results = {}

    for name, (data, sample_rate) in streams.items():
        # Resample if needed
        if sample_rate != target_rate:
            num_samples = int(len(data) * target_rate / sample_rate)
            data = scipy_signal.resample(data, num_samples)
            sample_rate = target_rate

        # Decompose
        results[name] = decompose_signal(data, sample_rate)

    return results
