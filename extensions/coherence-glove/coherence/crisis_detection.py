"""
Biometric Crisis Detection Module.

Implements automatic emergency triggers based on multi-wave coherence patterns:
- Systemic collapse: All φ-bands drop simultaneously
- Fall + unresponsiveness: Accelerometer spike + signal loss
- Anaphylaxis pattern: GSR spike + HRV crash
- Cardiac pattern: FAST band spike + CORE collapse

Triggers EMERGENCY_OVERRIDE state in ACSP when patterns detected.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable, Tuple, Any
from enum import Enum
import numpy as np

from .multiwave_state import MultiWaveCoherenceState, BAND_ORDER

# φ-constants for thresholds
PHI_INVERSE = 0.618033988749895
PHI_INV_2 = PHI_INVERSE ** 2  # 0.382
PHI_INV_3 = PHI_INVERSE ** 3  # 0.236


class CrisisType(Enum):
    """Types of detectable biometric crises."""
    SYSTEMIC_COLLAPSE = "systemic_collapse"
    FALL_UNRESPONSIVE = "fall_unresponsive"
    ANAPHYLAXIS = "anaphylaxis"
    CARDIAC = "cardiac"
    MULTI_BAND_CRASH = "multi_band_crash"
    COHERENCE_FREEFALL = "coherence_freefall"


class CrisisSeverity(Enum):
    """Severity levels for detected crises.

    Values are ordered: EMERGENCY (0) < CRITICAL (1) < WARNING (2) < WATCH (3)
    Lower value = more severe. This enables min() for highest severity.
    """
    EMERGENCY = 0  # Life-threatening
    CRITICAL = 1   # Immediate action required
    WARNING = 2    # Needs attention
    WATCH = 3      # Concerning but not urgent

    def __lt__(self, other):
        if isinstance(other, CrisisSeverity):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, CrisisSeverity):
            return self.value <= other.value
        return NotImplemented


@dataclass
class CrisisThresholds:
    """Thresholds for crisis detection.

    All thresholds use φ-based values for natural transitions.
    """
    # Systemic collapse: all bands below this
    systemic_band_threshold: float = PHI_INV_2  # 0.382

    # Band crash: individual band drops by this ratio
    band_crash_ratio: float = 0.5  # 50% drop

    # Coherence thresholds
    coherence_critical: float = PHI_INV_3  # 0.236
    coherence_freefall_drop: float = 0.3  # 0.3 drop in < 5s

    # GSR/HRV for anaphylaxis
    gsr_spike_ratio: float = 2.0  # 2x baseline
    hrv_crash_ratio: float = 0.3  # 70% drop

    # Cardiac pattern
    fast_band_spike_ratio: float = 2.5  # FAST band spike
    core_collapse_ratio: float = 0.4  # CORE drops 60%

    # Fall detection
    fall_acceleration_g: float = 3.0  # 3g impact
    unresponsive_timeout_s: float = 30.0  # No signal for 30s

    # Time windows
    pattern_window_s: float = 10.0  # Look-back window
    confirmation_samples: int = 3  # Required samples to confirm


@dataclass
class CrisisEvent:
    """A detected crisis event."""
    type: CrisisType
    severity: CrisisSeverity
    timestamp: datetime
    coherence_at_detection: float
    band_amplitudes: np.ndarray
    pattern_details: Dict[str, Any]
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.type.value,
            'severity': self.severity.name.lower(),
            'timestamp': self.timestamp.isoformat(),
            'coherence': self.coherence_at_detection,
            'band_amplitudes': self.band_amplitudes.tolist(),
            'pattern_details': self.pattern_details,
            'confidence': self.confidence,
        }


@dataclass
class CrisisHistory:
    """Recent state history for pattern detection."""
    timestamps: List[datetime] = field(default_factory=list)
    coherences: List[float] = field(default_factory=list)
    band_amplitudes: List[np.ndarray] = field(default_factory=list)
    signal_coherences: List[Dict[str, float]] = field(default_factory=list)

    max_length: int = 100

    def append(self, state: MultiWaveCoherenceState) -> None:
        """Add a coherence state to history."""
        self.timestamps.append(state.timestamp)
        self.coherences.append(state.scalar_coherence)
        self.band_amplitudes.append(state.band_amplitudes.copy())
        self.signal_coherences.append(dict(state.signal_coherences))

        # Prune old entries
        while len(self.timestamps) > self.max_length:
            self.timestamps.pop(0)
            self.coherences.pop(0)
            self.band_amplitudes.pop(0)
            self.signal_coherences.pop(0)

    def get_window(self, seconds: float) -> 'CrisisHistory':
        """Get entries within the last N seconds."""
        if not self.timestamps:
            return CrisisHistory()

        cutoff = datetime.now() - timedelta(seconds=seconds)
        result = CrisisHistory()

        for i, ts in enumerate(self.timestamps):
            if ts >= cutoff:
                result.timestamps.append(ts)
                result.coherences.append(self.coherences[i])
                result.band_amplitudes.append(self.band_amplitudes[i])
                result.signal_coherences.append(self.signal_coherences[i])

        return result

    @property
    def duration_s(self) -> float:
        """Duration of history in seconds."""
        if len(self.timestamps) < 2:
            return 0.0
        return (self.timestamps[-1] - self.timestamps[0]).total_seconds()


class CrisisDetector:
    """
    Detects biometric crisis patterns from coherence state history.

    Monitors MultiWaveCoherenceState updates and triggers emergency
    callbacks when crisis patterns are detected.

    Detection patterns:
    1. Systemic Collapse: All φ-bands drop below threshold simultaneously
    2. Fall + Unresponsive: Impact signature followed by signal loss
    3. Anaphylaxis: GSR spike combined with HRV crash
    4. Cardiac: FAST band spike with CORE collapse
    5. Coherence Freefall: Rapid coherence drop (> 0.3 in < 5s)
    """

    def __init__(
        self,
        thresholds: Optional[CrisisThresholds] = None,
        on_crisis: Optional[Callable[[CrisisEvent], None]] = None,
        on_emergency: Optional[Callable[[], None]] = None,
    ):
        """Initialize crisis detector.

        Args:
            thresholds: Detection thresholds
            on_crisis: Callback when crisis detected
            on_emergency: Callback to trigger EMERGENCY_OVERRIDE
        """
        self.thresholds = thresholds or CrisisThresholds()
        self.on_crisis = on_crisis
        self.on_emergency = on_emergency

        self._history = CrisisHistory()
        self._active_crises: List[CrisisEvent] = []
        self._last_state: Optional[MultiWaveCoherenceState] = None
        self._baseline_amplitudes: Optional[np.ndarray] = None
        self._signal_baselines: Dict[str, float] = {}

        # Tracking for specific patterns
        self._fall_detected_at: Optional[datetime] = None
        self._last_signal_time: datetime = datetime.now()

    def update(self, state: MultiWaveCoherenceState) -> List[CrisisEvent]:
        """
        Update detector with new coherence state.

        Args:
            state: New MultiWaveCoherenceState

        Returns:
            List of newly detected crisis events
        """
        self._history.append(state)
        self._last_signal_time = datetime.now()

        detected = []

        # Update baselines if healthy
        if state.scalar_coherence > PHI_INVERSE:
            self._update_baselines(state)

        # Run all pattern detectors
        patterns = [
            self._detect_systemic_collapse,
            self._detect_coherence_freefall,
            self._detect_multi_band_crash,
            self._detect_cardiac_pattern,
            self._detect_anaphylaxis_pattern,
        ]

        for detector in patterns:
            event = detector(state)
            if event is not None:
                detected.append(event)
                self._handle_crisis(event)

        self._last_state = state
        return detected

    def check_unresponsive(self) -> Optional[CrisisEvent]:
        """
        Check for unresponsive state (no signals for timeout).

        Should be called periodically by the main loop.
        """
        elapsed = (datetime.now() - self._last_signal_time).total_seconds()

        if elapsed > self.thresholds.unresponsive_timeout_s:
            # Check if fall was recently detected
            if self._fall_detected_at is not None:
                fall_elapsed = (datetime.now() - self._fall_detected_at).total_seconds()
                if fall_elapsed < 60.0:  # Within 1 minute of fall
                    event = CrisisEvent(
                        type=CrisisType.FALL_UNRESPONSIVE,
                        severity=CrisisSeverity.EMERGENCY,
                        timestamp=datetime.now(),
                        coherence_at_detection=0.0,
                        band_amplitudes=np.zeros(5),
                        pattern_details={
                            'seconds_since_signal': elapsed,
                            'seconds_since_fall': fall_elapsed,
                        },
                        confidence=0.95,
                    )
                    self._handle_crisis(event)
                    return event

            # General unresponsive (no fall detected)
            if elapsed > self.thresholds.unresponsive_timeout_s * 2:
                event = CrisisEvent(
                    type=CrisisType.FALL_UNRESPONSIVE,
                    severity=CrisisSeverity.CRITICAL,
                    timestamp=datetime.now(),
                    coherence_at_detection=0.0,
                    band_amplitudes=np.zeros(5),
                    pattern_details={
                        'seconds_since_signal': elapsed,
                        'fall_detected': False,
                    },
                    confidence=0.8,
                )
                self._handle_crisis(event)
                return event

        return None

    def register_fall(self, acceleration_g: float) -> Optional[CrisisEvent]:
        """
        Register a fall event from accelerometer.

        Args:
            acceleration_g: Peak acceleration in g-force

        Returns:
            CrisisEvent if above threshold
        """
        if acceleration_g >= self.thresholds.fall_acceleration_g:
            self._fall_detected_at = datetime.now()

            # Not immediately EMERGENCY - wait for unresponsive confirmation
            event = CrisisEvent(
                type=CrisisType.FALL_UNRESPONSIVE,
                severity=CrisisSeverity.WARNING,
                timestamp=datetime.now(),
                coherence_at_detection=self._last_state.scalar_coherence if self._last_state else 0.0,
                band_amplitudes=self._last_state.band_amplitudes if self._last_state else np.zeros(5),
                pattern_details={
                    'acceleration_g': acceleration_g,
                    'awaiting_response': True,
                },
                confidence=0.9,
            )
            self._handle_crisis(event)
            return event

        return None

    def _update_baselines(self, state: MultiWaveCoherenceState) -> None:
        """Update baselines from healthy state."""
        if self._baseline_amplitudes is None:
            self._baseline_amplitudes = state.band_amplitudes.copy()
        else:
            # Exponential moving average
            alpha = 0.1
            self._baseline_amplitudes = (
                alpha * state.band_amplitudes +
                (1 - alpha) * self._baseline_amplitudes
            )

        # Update signal baselines
        for name, value in state.signal_coherences.items():
            if name not in self._signal_baselines:
                self._signal_baselines[name] = value
            else:
                self._signal_baselines[name] = (
                    0.1 * value + 0.9 * self._signal_baselines[name]
                )

    def _detect_systemic_collapse(
        self, state: MultiWaveCoherenceState
    ) -> Optional[CrisisEvent]:
        """Detect systemic collapse - all bands below threshold."""
        threshold = self.thresholds.systemic_band_threshold

        # All bands must be below threshold
        if np.all(state.band_amplitudes < threshold):
            # Confirm with history
            window = self._history.get_window(self.thresholds.pattern_window_s)
            if len(window.band_amplitudes) >= self.thresholds.confirmation_samples:
                recent = window.band_amplitudes[-self.thresholds.confirmation_samples:]
                all_collapsed = all(
                    np.all(amps < threshold) for amps in recent
                )

                if all_collapsed:
                    max_amp = float(np.max(state.band_amplitudes))
                    return CrisisEvent(
                        type=CrisisType.SYSTEMIC_COLLAPSE,
                        severity=CrisisSeverity.EMERGENCY,
                        timestamp=datetime.now(),
                        coherence_at_detection=state.scalar_coherence,
                        band_amplitudes=state.band_amplitudes.copy(),
                        pattern_details={
                            'max_band_amplitude': max_amp,
                            'threshold': threshold,
                            'all_bands_collapsed': True,
                            'confirmation_samples': self.thresholds.confirmation_samples,
                        },
                        confidence=0.95,
                    )

        return None

    def _detect_coherence_freefall(
        self, state: MultiWaveCoherenceState
    ) -> Optional[CrisisEvent]:
        """Detect rapid coherence drop."""
        window = self._history.get_window(5.0)  # 5 second window

        if len(window.coherences) >= 2:
            peak = max(window.coherences)
            current = state.scalar_coherence
            drop = peak - current

            if drop >= self.thresholds.coherence_freefall_drop:
                duration = window.duration_s

                return CrisisEvent(
                    type=CrisisType.COHERENCE_FREEFALL,
                    severity=CrisisSeverity.CRITICAL,
                    timestamp=datetime.now(),
                    coherence_at_detection=current,
                    band_amplitudes=state.band_amplitudes.copy(),
                    pattern_details={
                        'peak_coherence': peak,
                        'current_coherence': current,
                        'drop_magnitude': drop,
                        'drop_duration_s': duration,
                    },
                    confidence=min(0.95, 0.7 + drop),
                )

        return None

    def _detect_multi_band_crash(
        self, state: MultiWaveCoherenceState
    ) -> Optional[CrisisEvent]:
        """Detect multiple bands crashing simultaneously."""
        if self._baseline_amplitudes is None:
            return None

        crashed_bands = []
        threshold = self.thresholds.band_crash_ratio

        for i, name in enumerate(BAND_ORDER):
            baseline = self._baseline_amplitudes[i]
            if baseline > 0.1:  # Ignore if baseline is very low
                ratio = state.band_amplitudes[i] / baseline
                if ratio < threshold:
                    crashed_bands.append({
                        'band': name,
                        'baseline': float(baseline),
                        'current': float(state.band_amplitudes[i]),
                        'ratio': float(ratio),
                    })

        # Multi-band crash: 3+ bands crashed
        if len(crashed_bands) >= 3:
            severity = (
                CrisisSeverity.EMERGENCY if len(crashed_bands) >= 4
                else CrisisSeverity.CRITICAL
            )

            return CrisisEvent(
                type=CrisisType.MULTI_BAND_CRASH,
                severity=severity,
                timestamp=datetime.now(),
                coherence_at_detection=state.scalar_coherence,
                band_amplitudes=state.band_amplitudes.copy(),
                pattern_details={
                    'crashed_bands': crashed_bands,
                    'bands_affected': len(crashed_bands),
                },
                confidence=0.85 + 0.05 * len(crashed_bands),
            )

        return None

    def _detect_cardiac_pattern(
        self, state: MultiWaveCoherenceState
    ) -> Optional[CrisisEvent]:
        """Detect cardiac pattern: FAST spike + CORE collapse."""
        if self._baseline_amplitudes is None:
            return None

        # FAST is index 3, CORE is index 2 in BAND_ORDER
        fast_idx = BAND_ORDER.index('FAST')
        core_idx = BAND_ORDER.index('CORE')

        fast_baseline = self._baseline_amplitudes[fast_idx]
        core_baseline = self._baseline_amplitudes[core_idx]

        if fast_baseline < 0.1 or core_baseline < 0.1:
            return None

        fast_ratio = state.band_amplitudes[fast_idx] / fast_baseline
        core_ratio = state.band_amplitudes[core_idx] / core_baseline

        # FAST spike (> 2.5x) AND CORE collapse (< 0.4x)
        if (fast_ratio >= self.thresholds.fast_band_spike_ratio and
            core_ratio <= self.thresholds.core_collapse_ratio):

            return CrisisEvent(
                type=CrisisType.CARDIAC,
                severity=CrisisSeverity.EMERGENCY,
                timestamp=datetime.now(),
                coherence_at_detection=state.scalar_coherence,
                band_amplitudes=state.band_amplitudes.copy(),
                pattern_details={
                    'fast_ratio': float(fast_ratio),
                    'fast_baseline': float(fast_baseline),
                    'fast_current': float(state.band_amplitudes[fast_idx]),
                    'core_ratio': float(core_ratio),
                    'core_baseline': float(core_baseline),
                    'core_current': float(state.band_amplitudes[core_idx]),
                },
                confidence=0.9,
            )

        return None

    def _detect_anaphylaxis_pattern(
        self, state: MultiWaveCoherenceState
    ) -> Optional[CrisisEvent]:
        """Detect anaphylaxis: GSR spike + HRV crash."""
        # Need both GSR and HRV signals
        gsr_key = None
        hrv_key = None

        for key in state.signal_coherences:
            if 'gsr' in key.lower() or 'eda' in key.lower():
                gsr_key = key
            if 'hrv' in key.lower():
                hrv_key = key

        if gsr_key is None or hrv_key is None:
            return None

        if gsr_key not in self._signal_baselines or hrv_key not in self._signal_baselines:
            return None

        gsr_baseline = self._signal_baselines[gsr_key]
        hrv_baseline = self._signal_baselines[hrv_key]

        if gsr_baseline < 0.1 or hrv_baseline < 0.1:
            return None

        gsr_current = state.signal_coherences.get(gsr_key, 0)
        hrv_current = state.signal_coherences.get(hrv_key, 0)

        gsr_ratio = gsr_current / gsr_baseline
        hrv_ratio = hrv_current / hrv_baseline

        # GSR spike (> 2x) AND HRV crash (< 0.3x)
        if (gsr_ratio >= self.thresholds.gsr_spike_ratio and
            hrv_ratio <= self.thresholds.hrv_crash_ratio):

            return CrisisEvent(
                type=CrisisType.ANAPHYLAXIS,
                severity=CrisisSeverity.EMERGENCY,
                timestamp=datetime.now(),
                coherence_at_detection=state.scalar_coherence,
                band_amplitudes=state.band_amplitudes.copy(),
                pattern_details={
                    'gsr_signal': gsr_key,
                    'gsr_ratio': float(gsr_ratio),
                    'gsr_baseline': float(gsr_baseline),
                    'gsr_current': float(gsr_current),
                    'hrv_signal': hrv_key,
                    'hrv_ratio': float(hrv_ratio),
                    'hrv_baseline': float(hrv_baseline),
                    'hrv_current': float(hrv_current),
                },
                confidence=0.85,
            )

        return None

    def _handle_crisis(self, event: CrisisEvent) -> None:
        """Handle detected crisis event."""
        self._active_crises.append(event)

        # Prune old crises (keep last 20)
        while len(self._active_crises) > 20:
            self._active_crises.pop(0)

        # Fire callbacks
        if self.on_crisis:
            try:
                self.on_crisis(event)
            except Exception:
                pass

        # Trigger emergency for high severity
        if event.severity in (CrisisSeverity.EMERGENCY, CrisisSeverity.CRITICAL):
            if self.on_emergency:
                try:
                    self.on_emergency()
                except Exception:
                    pass

    @property
    def active_crises(self) -> List[CrisisEvent]:
        """Currently active crises."""
        # Filter to recent crises (last 5 minutes)
        cutoff = datetime.now() - timedelta(minutes=5)
        return [c for c in self._active_crises if c.timestamp >= cutoff]

    @property
    def is_in_crisis(self) -> bool:
        """Check if any crisis is active."""
        return len(self.active_crises) > 0

    @property
    def highest_severity(self) -> Optional[CrisisSeverity]:
        """Get highest severity of active crises."""
        if not self.active_crises:
            return None
        return min(c.severity for c in self.active_crises)  # Lower = more severe

    def reset(self) -> None:
        """Reset detector state."""
        self._history = CrisisHistory()
        self._active_crises.clear()
        self._last_state = None
        self._baseline_amplitudes = None
        self._signal_baselines.clear()
        self._fall_detected_at = None
        self._last_signal_time = datetime.now()

    def get_status(self) -> Dict[str, Any]:
        """Get detector status."""
        return {
            'is_in_crisis': self.is_in_crisis,
            'highest_severity': self.highest_severity.name.lower() if self.highest_severity else None,
            'active_crises': [c.to_dict() for c in self.active_crises],
            'history_samples': len(self._history.timestamps),
            'has_baseline': self._baseline_amplitudes is not None,
            'seconds_since_signal': (datetime.now() - self._last_signal_time).total_seconds(),
        }


def create_crisis_detector(
    on_crisis: Optional[Callable[[CrisisEvent], None]] = None,
    on_emergency: Optional[Callable[[], None]] = None,
) -> CrisisDetector:
    """Factory function to create crisis detector.

    Args:
        on_crisis: Callback for crisis events
        on_emergency: Callback for emergency trigger

    Returns:
        Configured CrisisDetector
    """
    return CrisisDetector(
        on_crisis=on_crisis,
        on_emergency=on_emergency,
    )


# CLI Demo
if __name__ == "__main__":
    import random

    print("\n=== CRISIS DETECTION DEMO ===\n")

    crises_detected = []

    def on_crisis(event: CrisisEvent):
        crises_detected.append(event)
        print(f"CRISIS DETECTED: {event.type.value} ({event.severity.name.lower()})")
        print(f"  Coherence: {event.coherence_at_detection:.3f}")
        print(f"  Confidence: {event.confidence:.2f}")
        print(f"  Details: {event.pattern_details}")
        print()

    def on_emergency():
        print(">>> EMERGENCY_OVERRIDE TRIGGERED <<<\n")

    detector = CrisisDetector(
        on_crisis=on_crisis,
        on_emergency=on_emergency,
    )

    # Simulate normal states to establish baseline
    print("Establishing baseline...")
    for i in range(10):
        state = MultiWaveCoherenceState(
            timestamp=datetime.now(),
            band_amplitudes=np.array([0.6, 0.7, 0.8, 0.65, 0.55]) + np.random.random(5) * 0.1,
            band_phases=np.random.random(5) * 2 * np.pi,
            signal_coherences={'hrv': 0.75, 'gsr': 0.5, 'breath': 0.8},
            intentionality=0.7,
            breath_entrained=True,
            breath_rate_hz=0.1,
            scalar_coherence=0.72,
            uncertainty=0.15,
        )
        detector.update(state)

    print(f"Baseline established. History: {len(detector._history.timestamps)} samples\n")

    # Simulate systemic collapse
    print("--- Simulating Systemic Collapse ---")
    for i in range(5):
        state = MultiWaveCoherenceState(
            timestamp=datetime.now(),
            band_amplitudes=np.array([0.1, 0.15, 0.2, 0.12, 0.08]),  # All low
            band_phases=np.random.random(5) * 2 * np.pi,
            signal_coherences={'hrv': 0.2, 'gsr': 0.15, 'breath': 0.1},
            intentionality=0.1,
            breath_entrained=False,
            breath_rate_hz=0.05,
            scalar_coherence=0.15,
            uncertainty=0.7,
        )
        detector.update(state)

    print(f"\nTotal crises detected: {len(crises_detected)}")
    print(f"Status: {detector.get_status()}")
