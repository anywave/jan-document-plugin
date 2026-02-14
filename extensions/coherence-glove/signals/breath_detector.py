"""
Breath signal detection and intentionality scoring.

Extracts breath signal, detects dominant frequency, checks entrainment
to φ-target, and computes intentionality score.

Breath is unique: the only high-frequency signal under direct voluntary control.
It serves as the user's control surface into the coherence system.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass
from typing import Optional, Tuple
from enum import Enum, auto
import numpy as np
from scipy import signal as scipy_signal
from scipy.stats import pearsonr

# Import φ-constants
try:
    from ra_constants import PHI_INVERSE, PHI, phi_power
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


# φ-scaled breath targets
PHI_BREATH_TARGET_HZ = PHI_INVERSE  # ~0.618 Hz ≈ 6 breaths/min (optimal)
PHI_BREATH_FAST_HZ = PHI  # ~1.618 Hz ≈ 10 breaths/min (stressed)
PHI_BREATH_SLOW_HZ = phi_power(-2)  # ~0.382 Hz ≈ 4 breaths/min (deep)

# Entrainment tolerance
ENTRAINMENT_TOLERANCE_HZ = 0.1  # ±0.1 Hz from target


class EntrainmentStatus(Enum):
    """Status of breath entrainment to φ-target."""
    NOT_DETECTED = auto()  # No clear breath rhythm
    CHAOTIC = auto()  # Irregular breathing
    APPROACHING = auto()  # Moving toward target
    ENTRAINED = auto()  # Locked to φ-target
    DEEP = auto()  # Slower than target (φ^-2)


@dataclass
class BreathState:
    """Current state of breath and intentionality.

    Attributes:
        rate_hz: Detected breath frequency in Hz
        rate_bpm: Breath rate in breaths per minute
        entrainment_status: Current entrainment status
        entrainment_error: Difference from target (Hz)
        intentionality_score: 0-1 score of intentional control
        regularity: 0-1 score of breath regularity
        hrv_coupling: 0-1 correlation with HRV signal
        confidence: 0-1 confidence in measurements
        target_hz: Current breath target frequency
    """
    rate_hz: float
    rate_bpm: float
    entrainment_status: EntrainmentStatus
    entrainment_error: float
    intentionality_score: float
    regularity: float
    hrv_coupling: float
    confidence: float
    target_hz: float = PHI_BREATH_TARGET_HZ

    @property
    def is_entrained(self) -> bool:
        """Check if breathing is entrained to target."""
        return self.entrainment_status == EntrainmentStatus.ENTRAINED

    @property
    def is_intentional(self) -> bool:
        """Check if breathing shows intentional control."""
        return self.intentionality_score > 0.5

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            'rate_hz': self.rate_hz,
            'rate_bpm': self.rate_bpm,
            'entrainment_status': self.entrainment_status.name,
            'entrainment_error': self.entrainment_error,
            'intentionality_score': self.intentionality_score,
            'regularity': self.regularity,
            'hrv_coupling': self.hrv_coupling,
            'confidence': self.confidence,
            'target_hz': self.target_hz,
            'is_entrained': self.is_entrained,
            'is_intentional': self.is_intentional
        }


def extract_breath_from_hrv(hrv_signal: np.ndarray,
                             sample_rate: float) -> np.ndarray:
    """Extract breath-related component from HRV signal.

    Respiratory Sinus Arrhythmia (RSA) causes HRV modulation
    at breath frequency. We can derive breath from HRV.

    Args:
        hrv_signal: HRV signal (inter-beat intervals or instantaneous HR)
        sample_rate: Sample rate in Hz

    Returns:
        Estimated breath signal
    """
    # Bandpass filter for typical breath frequencies (0.1 - 0.5 Hz)
    nyquist = sample_rate / 2.0
    low = max(0.1 / nyquist, 0.001)
    high = min(0.5 / nyquist, 0.999)

    if low >= high:
        return hrv_signal

    try:
        b, a = scipy_signal.butter(4, [low, high], btype='band')
        breath_estimate = scipy_signal.filtfilt(b, a, hrv_signal)
    except ValueError:
        breath_estimate = hrv_signal

    return breath_estimate


def detect_dominant_frequency(signal: np.ndarray,
                               sample_rate: float,
                               min_freq: float = 0.1,
                               max_freq: float = 0.8) -> Tuple[float, float]:
    """Detect the dominant frequency in a signal.

    Args:
        signal: Input signal
        sample_rate: Sample rate in Hz
        min_freq: Minimum frequency to consider
        max_freq: Maximum frequency to consider

    Returns:
        (dominant_frequency_hz, confidence)
    """
    if len(signal) < 10:
        return 0.0, 0.0

    # Remove DC offset
    signal = signal - np.mean(signal)

    # Compute power spectral density
    nperseg = min(len(signal), int(sample_rate * 10))  # Up to 10 second windows
    freqs, psd = scipy_signal.welch(signal, fs=sample_rate, nperseg=nperseg)

    # Find frequencies in valid range
    valid_mask = (freqs >= min_freq) & (freqs <= max_freq)
    if not np.any(valid_mask):
        return 0.0, 0.0

    valid_freqs = freqs[valid_mask]
    valid_psd = psd[valid_mask]

    # Find peak
    peak_idx = np.argmax(valid_psd)
    dominant_freq = valid_freqs[peak_idx]
    peak_power = valid_psd[peak_idx]

    # Confidence = peak power relative to total power in band
    total_power = np.sum(valid_psd)
    if total_power > 0:
        confidence = peak_power / total_power
    else:
        confidence = 0.0

    return dominant_freq, confidence


def compute_breath_regularity(signal: np.ndarray,
                               sample_rate: float,
                               expected_freq: float) -> float:
    """Compute regularity of breath signal.

    Regular breathing = consistent intervals = high regularity score.

    Args:
        signal: Breath signal
        sample_rate: Sample rate in Hz
        expected_freq: Expected breath frequency

    Returns:
        Regularity score 0-1
    """
    if len(signal) < int(sample_rate * 5):  # Need at least 5 seconds
        return 0.0

    # Find peaks (breath cycles)
    expected_distance = int(sample_rate / expected_freq) if expected_freq > 0 else 100
    min_distance = max(int(expected_distance * 0.5), 1)

    peaks, _ = scipy_signal.find_peaks(signal, distance=min_distance)

    if len(peaks) < 3:
        return 0.0

    # Calculate inter-peak intervals
    intervals = np.diff(peaks) / sample_rate

    # Regularity = 1 - coefficient of variation
    mean_interval = np.mean(intervals)
    if mean_interval > 0:
        cv = np.std(intervals) / mean_interval
        regularity = max(0.0, 1.0 - cv)
    else:
        regularity = 0.0

    return min(1.0, regularity)


def compute_hrv_coupling(breath_signal: np.ndarray,
                          hrv_signal: np.ndarray,
                          sample_rate: float) -> float:
    """Compute coupling between breath and HRV signals.

    Strong coupling indicates respiratory sinus arrhythmia (RSA),
    which reflects parasympathetic activity and intentional breath control.

    Args:
        breath_signal: Breath signal
        hrv_signal: HRV signal
        sample_rate: Sample rate (should be same for both)

    Returns:
        Coupling score 0-1
    """
    # Ensure same length
    min_len = min(len(breath_signal), len(hrv_signal))
    if min_len < 10:
        return 0.0

    breath_signal = breath_signal[:min_len]
    hrv_signal = hrv_signal[:min_len]

    # Normalize signals
    breath_norm = (breath_signal - np.mean(breath_signal))
    hrv_norm = (hrv_signal - np.mean(hrv_signal))

    breath_std = np.std(breath_norm)
    hrv_std = np.std(hrv_norm)

    if breath_std < 1e-10 or hrv_std < 1e-10:
        return 0.0

    breath_norm = breath_norm / breath_std
    hrv_norm = hrv_norm / hrv_std

    # Cross-correlation at zero lag
    try:
        correlation, _ = pearsonr(breath_norm, hrv_norm)
        coupling = abs(correlation)  # Absolute value since phase may differ
    except:
        coupling = 0.0

    return min(1.0, max(0.0, coupling))


def determine_entrainment_status(rate_hz: float,
                                  target_hz: float,
                                  regularity: float,
                                  confidence: float) -> EntrainmentStatus:
    """Determine entrainment status based on breath metrics.

    Args:
        rate_hz: Detected breath rate
        target_hz: Target breath rate (φ-scaled)
        regularity: Breath regularity score
        confidence: Detection confidence

    Returns:
        EntrainmentStatus enum value
    """
    if confidence < 0.3:
        return EntrainmentStatus.NOT_DETECTED

    if regularity < 0.3:
        return EntrainmentStatus.CHAOTIC

    error = abs(rate_hz - target_hz)

    # Check for deep breathing (slower than target)
    if rate_hz < PHI_BREATH_SLOW_HZ + 0.05:
        return EntrainmentStatus.DEEP

    # Check for entrainment
    if error < ENTRAINMENT_TOLERANCE_HZ:
        return EntrainmentStatus.ENTRAINED

    # Check if approaching target
    if error < ENTRAINMENT_TOLERANCE_HZ * 2:
        return EntrainmentStatus.APPROACHING

    return EntrainmentStatus.CHAOTIC


def compute_intentionality_score(regularity: float,
                                  hrv_coupling: float,
                                  entrainment_error: float) -> float:
    """Compute intentionality score from breath metrics.

    Intentionality = regularity × HRV coupling × (1 - normalized_error)

    High intentionality indicates:
    - User is breathing regularly (not chaotic)
    - Breath is coupled to HRV (physiological engagement)
    - Near target frequency (following guidance)

    Args:
        regularity: Breath regularity 0-1
        hrv_coupling: HRV coupling strength 0-1
        entrainment_error: Error from target in Hz

    Returns:
        Intentionality score 0-1
    """
    # Normalize entrainment error (error of 0.3 Hz → ~0)
    error_factor = max(0.0, 1.0 - entrainment_error / 0.3)

    # Combined intentionality
    intentionality = regularity * hrv_coupling * error_factor

    return min(1.0, max(0.0, intentionality))


def detect_breath_state(breath_signal: np.ndarray,
                         sample_rate: float,
                         hrv_signal: Optional[np.ndarray] = None,
                         target_hz: float = PHI_BREATH_TARGET_HZ) -> BreathState:
    """Detect current breath state and intentionality.

    Args:
        breath_signal: Breath signal array
        sample_rate: Sample rate in Hz
        hrv_signal: Optional HRV signal for coupling analysis
        target_hz: Target breath frequency

    Returns:
        BreathState with all metrics
    """
    # Detect dominant frequency
    rate_hz, confidence = detect_dominant_frequency(
        breath_signal, sample_rate, min_freq=0.1, max_freq=0.8
    )

    # Convert to BPM
    rate_bpm = rate_hz * 60.0

    # Compute regularity
    regularity = compute_breath_regularity(breath_signal, sample_rate, rate_hz)

    # Compute HRV coupling if available
    if hrv_signal is not None:
        # Resample HRV to match breath if needed
        if len(hrv_signal) != len(breath_signal):
            hrv_resampled = scipy_signal.resample(hrv_signal, len(breath_signal))
        else:
            hrv_resampled = hrv_signal
        hrv_coupling = compute_hrv_coupling(breath_signal, hrv_resampled, sample_rate)
    else:
        hrv_coupling = 0.5  # Default moderate coupling if no HRV available

    # Entrainment error
    entrainment_error = abs(rate_hz - target_hz)

    # Determine entrainment status
    entrainment_status = determine_entrainment_status(
        rate_hz, target_hz, regularity, confidence
    )

    # Compute intentionality
    intentionality_score = compute_intentionality_score(
        regularity, hrv_coupling, entrainment_error
    )

    return BreathState(
        rate_hz=rate_hz,
        rate_bpm=rate_bpm,
        entrainment_status=entrainment_status,
        entrainment_error=entrainment_error,
        intentionality_score=intentionality_score,
        regularity=regularity,
        hrv_coupling=hrv_coupling,
        confidence=confidence,
        target_hz=target_hz
    )


class BreathDetector:
    """Stateful breath detector for streaming analysis.

    Maintains history for more accurate detection over time.
    """

    def __init__(self,
                 sample_rate: float,
                 target_hz: float = PHI_BREATH_TARGET_HZ,
                 history_duration: float = 30.0):
        """Initialize breath detector.

        Args:
            sample_rate: Sample rate of breath signal
            target_hz: Target breath frequency (default φ^-1)
            history_duration: Duration of history to maintain
        """
        self.sample_rate = sample_rate
        self.target_hz = target_hz
        self.history_duration = history_duration

        # Rolling history buffers
        max_samples = int(sample_rate * history_duration)
        self._breath_history = np.zeros(max_samples)
        self._hrv_history = np.zeros(max_samples)
        self._position = 0
        self._filled = False

    def set_target(self, target_hz: float) -> None:
        """Update breath target frequency.

        Args:
            target_hz: New target in Hz
        """
        self.target_hz = target_hz

    def update(self,
               breath_chunk: np.ndarray,
               hrv_chunk: Optional[np.ndarray] = None) -> BreathState:
        """Update with new data and return current state.

        Args:
            breath_chunk: New breath signal chunk
            hrv_chunk: Optional new HRV chunk

        Returns:
            Current BreathState
        """
        # Add to history
        chunk_len = len(breath_chunk)
        buffer_len = len(self._breath_history)

        if chunk_len >= buffer_len:
            # Chunk larger than buffer - use latest samples
            self._breath_history[:] = breath_chunk[-buffer_len:]
            if hrv_chunk is not None:
                hrv_resampled = scipy_signal.resample(hrv_chunk, len(breath_chunk))
                self._hrv_history[:] = hrv_resampled[-buffer_len:]
            self._filled = True
        else:
            # Shift and append
            end_pos = self._position + chunk_len
            if end_pos <= buffer_len:
                self._breath_history[self._position:end_pos] = breath_chunk
                if hrv_chunk is not None:
                    hrv_resampled = scipy_signal.resample(hrv_chunk, chunk_len)
                    self._hrv_history[self._position:end_pos] = hrv_resampled
                self._position = end_pos
            else:
                # Wrap around
                overflow = end_pos - buffer_len
                self._breath_history[self._position:] = breath_chunk[:-overflow]
                self._breath_history[:overflow] = breath_chunk[-overflow:]
                if hrv_chunk is not None:
                    hrv_resampled = scipy_signal.resample(hrv_chunk, chunk_len)
                    self._hrv_history[self._position:] = hrv_resampled[:-overflow]
                    self._hrv_history[:overflow] = hrv_resampled[-overflow:]
                self._position = overflow
                self._filled = True

        # Get current view of history
        if self._filled:
            breath_data = np.roll(self._breath_history, -self._position)
            hrv_data = np.roll(self._hrv_history, -self._position)
        else:
            breath_data = self._breath_history[:self._position]
            hrv_data = self._hrv_history[:self._position]

        # Detect state
        return detect_breath_state(
            breath_data,
            self.sample_rate,
            hrv_signal=hrv_data if np.any(hrv_data != 0) else None,
            target_hz=self.target_hz
        )

    def reset(self) -> None:
        """Reset history buffers."""
        self._breath_history.fill(0)
        self._hrv_history.fill(0)
        self._position = 0
        self._filled = False
