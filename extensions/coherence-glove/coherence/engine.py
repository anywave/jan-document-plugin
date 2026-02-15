"""
Multi-Wave Coherence Engine.

Main orchestration class that ties together:
- Signal stream registry
- φ-band decomposition
- BTF temporal inference
- Coherence state computation

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime, timedelta
from enum import Enum
import threading
import numpy as np

# Signal processing
from signals import (
    SignalStream,
    StreamRegistry,
    create_stream,
    BandDecomposer,
    decompose_signal,
    BreathDetector,
    BreathState,
    PHI_BREATH_TARGET_HZ,
    BAND_ORDER,
)

# Coherence components
from .multiwave_state import MultiWaveCoherenceState
from .scalar_reduction import (
    compute_scalar_coherence,
    compute_uncertainty,
    coherence_to_consent_level,
    select_reference_phase,
)
from .streaming_btf import (
    StreamingBTF,
    AdaptiveStreamingBTF,
    StreamingConfig,
    StreamingState,
    create_streaming_btf,
)
from .btf_engine import BTFResult


class EngineState(Enum):
    """State of the coherence engine."""
    IDLE = "idle"
    WARMING_UP = "warming_up"
    RUNNING = "running"
    PAUSED = "paused"


@dataclass
class EngineConfig:
    """Configuration for the coherence engine.

    Attributes:
        window_duration_s: Processing window duration in seconds
        update_interval_s: Seconds between coherence updates
        min_signals: Minimum signals required to compute coherence
        breath_target_hz: Target breath rate (default: φ-scaled)
        intentionality_threshold: Threshold for intentional control
        use_btf: Whether to use BTF inference (vs. direct band decomp)
        adaptive_scheduling: Use adaptive update scheduling
    """
    window_duration_s: float = 60.0
    update_interval_s: float = 1.0
    min_signals: int = 1
    breath_target_hz: float = PHI_BREATH_TARGET_HZ
    intentionality_threshold: float = 0.5
    use_btf: bool = True
    adaptive_scheduling: bool = True


class MultiWaveCoherenceEngine:
    """Main coherence engine orchestrating the full pipeline.

    Flow:
        Signals -> Registry -> Band Decomposition -> BTF -> Coherence State

    The engine supports:
    - Multiple concurrent signal streams
    - Real-time streaming with configurable update rate
    - Breath-based intentionality detection
    - BTF temporal inference for robust estimation
    - Thread-safe state access
    """

    def __init__(self,
                 config: Optional[EngineConfig] = None,
                 on_state_update: Optional[Callable[[MultiWaveCoherenceState], None]] = None):
        """Initialize coherence engine.

        Args:
            config: Engine configuration
            on_state_update: Callback when new coherence state available
        """
        self.config = config or EngineConfig()
        self.on_state_update = on_state_update

        # Components
        self._registry = StreamRegistry()
        self._band_decomposers: Dict[str, BandDecomposer] = {}  # Per-stream decomposers
        self._breath_detector: Optional[BreathDetector] = None  # Lazy init
        self._breath_sample_rate: Optional[float] = None

        # BTF streaming processor (initialized when streams registered)
        self._streaming_btf: Optional[StreamingBTF] = None

        # State
        self._state = EngineState.IDLE
        self._current_coherence: Optional[MultiWaveCoherenceState] = None
        self._current_breath: Optional[BreathState] = None
        self._lock = threading.RLock()

        # Processing history
        self._last_update = datetime.now()
        self._update_count = 0

    @property
    def state(self) -> EngineState:
        """Current engine state."""
        return self._state

    @property
    def registered_streams(self) -> List[str]:
        """Names of registered signal streams."""
        return list(self._registry._streams.keys())

    def register_stream(self, stream: SignalStream) -> None:
        """Register a signal stream for processing.

        Args:
            stream: Signal stream to register
        """
        with self._lock:
            self._registry.register(stream)

            # Reinitialize BTF if needed
            n_streams = len(self._registry._streams)
            if self.config.use_btf:
                self._init_btf(n_streams)

            if self._state == EngineState.IDLE and n_streams >= self.config.min_signals:
                self._state = EngineState.WARMING_UP

    def register_stream_data(self,
                              name: str,
                              data: np.ndarray,
                              sample_rate: float,
                              quality_mask: Optional[np.ndarray] = None) -> None:
        """Convenience method to register stream from raw data.

        Args:
            name: Stream name (e.g., 'hrv', 'breath', 'eda')
            data: Signal data array
            sample_rate: Sample rate in Hz
            quality_mask: Optional quality mask
        """
        stream = create_stream(
            name=name,
            data=data,
            sample_rate=sample_rate,
            quality_mask=quality_mask,
        )
        self.register_stream(stream)

    def _init_btf(self, n_signals: int) -> None:
        """Initialize or reinitialize BTF processor."""
        btf_config = StreamingConfig(
            window_size=int(self.config.window_duration_s * 4),  # ~4 samples/s typical
            update_interval_s=self.config.update_interval_s,
            min_samples_for_update=5,
            real_time_mode=True,
        )

        # Use 5 factors regardless of signal count (φ-bands)
        n_factors = 5

        if self.config.adaptive_scheduling:
            self._streaming_btf = AdaptiveStreamingBTF(
                n_signals=n_factors,  # Factors, not raw signals
                config=btf_config,
                on_update=self._on_btf_update,
            )
        else:
            self._streaming_btf = StreamingBTF(
                n_signals=n_factors,
                config=btf_config,
                on_update=self._on_btf_update,
            )

    def _on_btf_update(self, result: BTFResult) -> None:
        """Handle BTF update - compute coherence state."""
        self._compute_state_from_btf(result)

    def process_window(self) -> Optional[MultiWaveCoherenceState]:
        """Process current window and compute coherence state.

        Returns:
            MultiWaveCoherenceState if computation successful, None otherwise
        """
        with self._lock:
            if len(self._registry._streams) < self.config.min_signals:
                return None

            # Get aligned windows from all streams
            try:
                windows = self._registry.get_aligned_windows(
                    duration_sec=self.config.window_duration_s
                )
            except Exception as e:
                return None

            if not windows:
                return None

            # Decompose each stream into φ-bands
            decompositions = {}
            for name, stream in windows.items():
                data = stream.data
                sr = stream.sample_rate
                if len(data) < 10:
                    continue
                decomp = decompose_signal(data, sr)
                decompositions[name] = decomp

            if not decompositions:
                return None

            # Detect breath state
            breath_state = self._detect_breath(windows)
            self._current_breath = breath_state

            # Compute coherence
            if self.config.use_btf and self._streaming_btf is not None:
                # Feed band data to BTF
                state = self._compute_via_btf(decompositions, breath_state)
            else:
                # Direct computation without BTF
                state = self._compute_direct(decompositions, breath_state)

            if state is not None:
                self._current_coherence = state
                self._last_update = datetime.now()
                self._update_count += 1

                if self._state == EngineState.WARMING_UP:
                    self._state = EngineState.RUNNING

                if self.on_state_update is not None:
                    try:
                        self.on_state_update(state)
                    except Exception:
                        pass

            return state

    def _get_breath_detector(self, sample_rate: float) -> BreathDetector:
        """Get or create breath detector for the given sample rate."""
        if self._breath_detector is None or self._breath_sample_rate != sample_rate:
            self._breath_detector = BreathDetector(
                sample_rate=sample_rate,
                target_hz=self.config.breath_target_hz,
            )
            self._breath_sample_rate = sample_rate
        return self._breath_detector

    def _detect_breath(self, windows: Dict) -> Optional[BreathState]:
        """Detect breath state from available signals.

        Note: Raw PPG data is NOT fed as HRV because PPG oscillates at
        cardiac frequency (~1Hz), while HRV requires peak-detection → IBI
        extraction. Feeding raw PPG kills hrv_coupling (0.5 default → ~0).
        Proper HRV extraction can be added as a future enhancement.
        """
        # Check for explicit breath signal
        if 'breath' in windows or 'resp' in windows:
            breath_key = 'breath' if 'breath' in windows else 'resp'
            stream = windows[breath_key]
            detector = self._get_breath_detector(stream.sample_rate)
            return detector.update(stream.data)

        # Try to extract from HRV using RSA
        if 'hrv' in windows:
            from signals.breath_detector import extract_breath_from_hrv
            stream = windows['hrv']
            breath_signal = extract_breath_from_hrv(stream.data, stream.sample_rate)
            detector = self._get_breath_detector(stream.sample_rate)
            return detector.update(breath_signal)

        return None

    def _compute_via_btf(self,
                         decompositions: Dict,
                         breath_state: Optional[BreathState]) -> Optional[MultiWaveCoherenceState]:
        """Compute coherence using BTF inference."""
        # Aggregate band amplitudes across streams
        band_amps = np.zeros(5)
        band_phases = np.zeros(5)
        signal_coherences = {}

        n_streams = 0
        for name, decomp in decompositions.items():
            band_amps += decomp.amplitudes
            band_phases += decomp.phases
            signal_coherences[name] = float(np.mean(decomp.amplitudes))
            n_streams += 1

        if n_streams > 0:
            band_amps /= n_streams
            band_phases /= n_streams
            # Normalize phases to [-pi, pi]
            band_phases = np.angle(np.exp(1j * band_phases))

        # Push to streaming BTF
        if self._streaming_btf is not None:
            sample = band_amps  # Use amplitudes as observation
            self._streaming_btf.push_sample(sample)

            # Get latest BTF result
            btf_result = self._streaming_btf.latest_result
            if btf_result is not None:
                # Use BTF factors to refine estimates
                band_amps = btf_result.band_amplitudes
                band_phases = btf_result.band_phases

        # Compute intentionality from breath
        intentionality = 0.0
        breath_entrained = False
        breath_rate_hz = 0.0
        breath_phase = None

        if breath_state is not None:
            intentionality = breath_state.intentionality_score
            breath_entrained = breath_state.is_entrained
            breath_rate_hz = breath_state.rate_hz
            breath_phase = None  # BreathState doesn't track phase directly

        # Select reference phase
        reference_phase = select_reference_phase(
            band_phases,
            breath_phase,
            intentionality,
            self.config.intentionality_threshold,
            band_amplitudes=band_amps,
        )

        # Compute scalar coherence
        scalar = compute_scalar_coherence(
            band_amps,
            band_phases,
            intentionality,
            breath_phase,
            self.config.intentionality_threshold,
            reference_phase,
        )

        # Compute uncertainty
        uncertainty = compute_uncertainty(band_amps, signal_coherences)

        # Build state
        btf_factors = None
        if self._streaming_btf is not None and self._streaming_btf.latest_result is not None:
            btf_factors = self._streaming_btf.latest_result.to_dict()

        return MultiWaveCoherenceState(
            timestamp=datetime.now(),
            band_amplitudes=band_amps,
            band_phases=band_phases,
            signal_coherences=signal_coherences,
            intentionality=intentionality,
            breath_entrained=breath_entrained,
            breath_rate_hz=breath_rate_hz,
            scalar_coherence=scalar,
            uncertainty=uncertainty,
            reference_phase=reference_phase,
            btf_factors=btf_factors,
        )

    def _compute_state_from_btf(self, btf_result: BTFResult) -> None:
        """Compute coherence state from BTF result callback."""
        # This is called when BTF updates asynchronously
        # Re-use cached breath state
        breath_state = self._current_breath

        band_amps = btf_result.band_amplitudes
        band_phases = btf_result.band_phases

        intentionality = 0.0
        breath_entrained = False
        breath_rate_hz = 0.0
        breath_phase = None

        if breath_state is not None:
            intentionality = breath_state.intentionality_score
            breath_entrained = breath_state.is_entrained
            breath_rate_hz = breath_state.rate_hz
            breath_phase = None  # BreathState doesn't track phase directly

        reference_phase = select_reference_phase(
            band_phases,
            breath_phase,
            intentionality,
            self.config.intentionality_threshold,
            band_amplitudes=band_amps,
        )

        scalar = compute_scalar_coherence(
            band_amps,
            band_phases,
            intentionality,
            breath_phase,
            self.config.intentionality_threshold,
            reference_phase,
        )

        uncertainty = compute_uncertainty(band_amps)

        state = MultiWaveCoherenceState(
            timestamp=datetime.now(),
            band_amplitudes=band_amps,
            band_phases=band_phases,
            signal_coherences={},  # Not available from BTF alone
            intentionality=intentionality,
            breath_entrained=breath_entrained,
            breath_rate_hz=breath_rate_hz,
            scalar_coherence=scalar,
            uncertainty=uncertainty,
            reference_phase=reference_phase,
            btf_factors=btf_result.to_dict(),
        )

        with self._lock:
            self._current_coherence = state
            self._last_update = datetime.now()
            self._update_count += 1

        if self.on_state_update is not None:
            try:
                self.on_state_update(state)
            except Exception:
                pass

    def _compute_direct(self,
                        decompositions: Dict,
                        breath_state: Optional[BreathState]) -> Optional[MultiWaveCoherenceState]:
        """Compute coherence directly without BTF."""
        # Aggregate band data
        band_amps = np.zeros(5)
        band_phases = np.zeros(5)
        signal_coherences = {}

        n_streams = 0
        for name, decomp in decompositions.items():
            band_amps += decomp.amplitudes
            band_phases += decomp.phases
            signal_coherences[name] = float(np.mean(decomp.amplitudes))
            n_streams += 1

        if n_streams > 0:
            band_amps /= n_streams
            band_phases /= n_streams
            band_phases = np.angle(np.exp(1j * band_phases))

        # Breath
        intentionality = 0.0
        breath_entrained = False
        breath_rate_hz = 0.0
        breath_phase = None

        if breath_state is not None:
            intentionality = breath_state.intentionality_score
            breath_entrained = breath_state.is_entrained
            breath_rate_hz = breath_state.rate_hz
            breath_phase = None  # BreathState doesn't track phase directly

        reference_phase = select_reference_phase(
            band_phases,
            breath_phase,
            intentionality,
            self.config.intentionality_threshold,
            band_amplitudes=band_amps,
        )

        scalar = compute_scalar_coherence(
            band_amps,
            band_phases,
            intentionality,
            breath_phase,
            self.config.intentionality_threshold,
            reference_phase,
        )

        uncertainty = compute_uncertainty(band_amps, signal_coherences)

        return MultiWaveCoherenceState(
            timestamp=datetime.now(),
            band_amplitudes=band_amps,
            band_phases=band_phases,
            signal_coherences=signal_coherences,
            intentionality=intentionality,
            breath_entrained=breath_entrained,
            breath_rate_hz=breath_rate_hz,
            scalar_coherence=scalar,
            uncertainty=uncertainty,
            reference_phase=reference_phase,
        )

    def get_current_state(self) -> Optional[MultiWaveCoherenceState]:
        """Get most recent coherence state.

        Returns:
            Current MultiWaveCoherenceState or None if not yet computed
        """
        with self._lock:
            return self._current_coherence

    def get_consent_level(self) -> str:
        """Get current consent level string.

        Returns:
            Consent level: 'FULL_CONSENT', 'DIMINISHED', 'SUSPENDED', or 'EMERGENCY'
        """
        state = self.get_current_state()
        if state is None:
            return 'EMERGENCY'  # Unknown state = maximum caution

        return coherence_to_consent_level(
            state.scalar_coherence,
            state.intentionality,
        )

    def set_breath_target(self, target_hz: float) -> None:
        """Set target breath rate for entrainment.

        Args:
            target_hz: Target breath rate in Hz
        """
        self.config.breath_target_hz = target_hz
        self._breath_detector = None  # Clear to recreate with new target

    def push_samples(self,
                     stream_name: str,
                     samples: np.ndarray,
                     quality_mask: Optional[np.ndarray] = None) -> Optional[MultiWaveCoherenceState]:
        """Push new samples to a stream and potentially trigger update.

        Args:
            stream_name: Name of the stream
            samples: New sample data
            quality_mask: Optional quality mask

        Returns:
            MultiWaveCoherenceState if update triggered
        """
        with self._lock:
            if stream_name not in self._registry._streams:
                raise ValueError(f"Unknown stream: {stream_name}")

            stream = self._registry._streams[stream_name]

            # Append to stream data (simplified - real impl would be more sophisticated)
            new_data = np.concatenate([stream.data, samples])
            if quality_mask is not None:
                new_mask = np.concatenate([stream.quality_mask, quality_mask])
            else:
                new_mask = np.concatenate([
                    stream.quality_mask,
                    np.ones(len(samples))
                ])

            # Truncate to window size
            max_samples = int(self.config.window_duration_s * stream.sample_rate * 1.5)
            if len(new_data) > max_samples:
                new_data = new_data[-max_samples:]
                new_mask = new_mask[-max_samples:]

            # Update stream
            self._registry._streams[stream_name] = SignalStream(
                name=stream.name,
                stream_type=stream.stream_type,
                data=new_data,
                sample_rate=stream.sample_rate,
                quality_mask=new_mask,
                metadata=stream.metadata,
            )

        # Check if update needed
        elapsed = (datetime.now() - self._last_update).total_seconds()
        if elapsed >= self.config.update_interval_s:
            return self.process_window()

        return None

    def pause(self) -> None:
        """Pause coherence updates."""
        self._state = EngineState.PAUSED

    def resume(self) -> None:
        """Resume coherence updates."""
        if self._state == EngineState.PAUSED:
            self._state = EngineState.RUNNING

    def reset(self) -> None:
        """Reset engine state."""
        with self._lock:
            self._registry = StreamRegistry()
            self._current_coherence = None
            self._current_breath = None
            self._breath_detector = None
            self._breath_sample_rate = None
            self._last_update = datetime.now()
            self._update_count = 0
            self._state = EngineState.IDLE

            if self._streaming_btf is not None:
                self._streaming_btf.reset()
                self._streaming_btf = None

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        stats = {
            'state': self._state.value,
            'update_count': self._update_count,
            'registered_streams': self.registered_streams,
            'last_update': self._last_update.isoformat() if self._last_update else None,
        }

        if self._streaming_btf is not None:
            btf_stats = self._streaming_btf.stats
            stats['btf'] = {
                'total_updates': btf_stats.total_updates,
                'avg_inference_ms': btf_stats.avg_inference_time_ms,
                'degraded_updates': btf_stats.degraded_updates,
            }

        if self._current_coherence is not None:
            stats['current'] = {
                'coherence': self._current_coherence.scalar_coherence,
                'consent_level': self.get_consent_level(),
                'intentionality': self._current_coherence.intentionality,
            }

        return stats


def create_coherence_engine(
    window_duration_s: float = 60.0,
    update_interval_s: float = 1.0,
    use_btf: bool = True,
    on_state_update: Optional[Callable[[MultiWaveCoherenceState], None]] = None,
) -> MultiWaveCoherenceEngine:
    """Factory function to create a coherence engine.

    Args:
        window_duration_s: Processing window duration
        update_interval_s: Update interval
        use_btf: Whether to use BTF inference
        on_state_update: Callback for state updates

    Returns:
        Configured MultiWaveCoherenceEngine
    """
    config = EngineConfig(
        window_duration_s=window_duration_s,
        update_interval_s=update_interval_s,
        use_btf=use_btf,
    )
    return MultiWaveCoherenceEngine(config, on_state_update)
