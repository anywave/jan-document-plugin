"""
Streaming BTF for Online Coherence Inference.

Provides incremental BTF updates with rolling posterior state,
supporting real-time coherence monitoring without reprocessing
full history.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading
import time
import numpy as np

from .btf_engine import BTFEngine, BTFResult, create_btf_engine


class StreamingState(Enum):
    """State of the streaming processor."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    BEHIND = "behind"  # Falling behind real-time


@dataclass
class StreamingConfig:
    """Configuration for streaming BTF.

    Attributes:
        window_size: Number of time points in sliding window
        update_interval_s: Seconds between BTF updates
        min_samples_for_update: Minimum new samples before update
        max_lag_s: Maximum lag before degraded mode
        real_time_mode: Use reduced iterations for speed
    """
    window_size: int = 50
    update_interval_s: float = 1.0
    min_samples_for_update: int = 5
    max_lag_s: float = 2.0
    real_time_mode: bool = True


@dataclass
class StreamingStats:
    """Statistics about streaming performance."""
    total_updates: int = 0
    total_samples: int = 0
    avg_inference_time_ms: float = 0.0
    max_inference_time_ms: float = 0.0
    degraded_updates: int = 0
    last_update_time: Optional[datetime] = None

    def record_update(self, inference_time_s: float, degraded: bool = False):
        """Record an update for statistics."""
        self.total_updates += 1
        time_ms = inference_time_s * 1000

        # Running average
        if self.total_updates == 1:
            self.avg_inference_time_ms = time_ms
        else:
            self.avg_inference_time_ms = (
                self.avg_inference_time_ms * (self.total_updates - 1) + time_ms
            ) / self.total_updates

        self.max_inference_time_ms = max(self.max_inference_time_ms, time_ms)
        if degraded:
            self.degraded_updates += 1
        self.last_update_time = datetime.now()


class StreamingBTF:
    """Streaming BTF processor for real-time coherence inference.

    Maintains a sliding window of observations and performs
    incremental BTF updates using warm start from previous posterior.
    """

    def __init__(self,
                 n_signals: int,
                 config: Optional[StreamingConfig] = None,
                 on_update: Optional[Callable[[BTFResult], None]] = None):
        """Initialize streaming BTF.

        Args:
            n_signals: Number of input signal streams
            config: Streaming configuration
            on_update: Callback when new BTF result available
        """
        self.n_signals = n_signals
        self.config = config or StreamingConfig()
        self.on_update = on_update

        # Create BTF engine
        self._engine = create_btf_engine(real_time=self.config.real_time_mode)

        # Observation buffer (deque for efficient sliding window)
        self._buffer: deque = deque(maxlen=self.config.window_size)
        self._mask_buffer: deque = deque(maxlen=self.config.window_size)
        self._timestamps: deque = deque(maxlen=self.config.window_size)

        # State
        self._state = StreamingState.IDLE
        self._lock = threading.RLock()
        self._latest_result: Optional[BTFResult] = None
        self._stats = StreamingStats()

        # Scheduling
        self._last_update = datetime.now()
        self._samples_since_update = 0

        # Background thread (optional)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @property
    def state(self) -> StreamingState:
        """Current streaming state."""
        return self._state

    @property
    def latest_result(self) -> Optional[BTFResult]:
        """Most recent BTF result."""
        with self._lock:
            return self._latest_result

    @property
    def stats(self) -> StreamingStats:
        """Performance statistics."""
        return self._stats

    @property
    def buffer_fill(self) -> float:
        """Fraction of buffer filled (0-1)."""
        return len(self._buffer) / self.config.window_size

    def push_sample(self,
                    sample: np.ndarray,
                    mask: Optional[np.ndarray] = None,
                    timestamp: Optional[datetime] = None) -> Optional[BTFResult]:
        """Push a new sample and potentially trigger update.

        Args:
            sample: Observation vector (n_signals,)
            mask: Binary mask (1=observed), default all observed
            timestamp: Sample timestamp, default now

        Returns:
            BTFResult if update was triggered, None otherwise
        """
        if len(sample) != self.n_signals:
            raise ValueError(f"Expected {self.n_signals} signals, got {len(sample)}")

        if mask is None:
            mask = np.ones(self.n_signals)

        with self._lock:
            self._buffer.append(sample.copy())
            self._mask_buffer.append(mask.copy())
            self._timestamps.append(timestamp or datetime.now())
            self._samples_since_update += 1
            self._stats.total_samples += 1

        # Check if update needed
        if self._should_update():
            return self._perform_update()

        return None

    def push_batch(self,
                   samples: np.ndarray,
                   masks: Optional[np.ndarray] = None) -> Optional[BTFResult]:
        """Push multiple samples at once.

        Args:
            samples: Observation matrix (T × n_signals)
            masks: Binary masks (T × n_signals)

        Returns:
            BTFResult if update was triggered
        """
        T = samples.shape[0]
        if masks is None:
            masks = np.ones_like(samples)

        result = None
        for t in range(T):
            r = self.push_sample(samples[t, :], masks[t, :])
            if r is not None:
                result = r

        return result

    def _should_update(self) -> bool:
        """Check if BTF update should be triggered."""
        # Not enough samples
        if len(self._buffer) < self.config.min_samples_for_update:
            return False

        if self._samples_since_update < self.config.min_samples_for_update:
            return False

        # Time-based trigger
        elapsed = (datetime.now() - self._last_update).total_seconds()
        return elapsed >= self.config.update_interval_s

    def _perform_update(self, force_degraded: bool = False) -> BTFResult:
        """Perform BTF inference update.

        Args:
            force_degraded: Force degraded mode (fewer iterations)

        Returns:
            BTFResult from inference
        """
        with self._lock:
            # Build observation matrix from buffer
            Y = np.array(list(self._buffer)).T  # N × T
            mask = np.array(list(self._mask_buffer)).T

        # Check lag
        elapsed = (datetime.now() - self._last_update).total_seconds()
        is_behind = elapsed > self.config.max_lag_s

        if is_behind or force_degraded:
            self._state = StreamingState.BEHIND
            # Reduce iterations for catchup
            prev_iters = self._engine.n_iter
            self._engine.n_iter = max(10, prev_iters // 2)
        else:
            self._state = StreamingState.RUNNING

        # Perform inference
        t_start = time.time()
        result = self._engine.fit(Y, mask=mask, warm_start=True)
        t_elapsed = time.time() - t_start

        # Restore iterations if degraded
        if is_behind or force_degraded:
            self._engine.n_iter = prev_iters if 'prev_iters' in dir() else 25

        # Update state
        with self._lock:
            self._latest_result = result
            self._last_update = datetime.now()
            self._samples_since_update = 0
            self._stats.record_update(t_elapsed, degraded=is_behind)

        # Callback
        if self.on_update is not None:
            try:
                self.on_update(result)
            except Exception as e:
                pass  # Don't let callback errors break streaming

        return result

    def force_update(self) -> Optional[BTFResult]:
        """Force an immediate update regardless of timing."""
        if len(self._buffer) < 5:
            return None
        return self._perform_update()

    def start_background(self) -> None:
        """Start background update thread."""
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._background_loop, daemon=True)
        self._thread.start()

    def stop_background(self) -> None:
        """Stop background update thread."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        self._state = StreamingState.IDLE

    def _background_loop(self) -> None:
        """Background thread loop for periodic updates."""
        while not self._stop_event.is_set():
            if self._should_update():
                try:
                    self._perform_update()
                except Exception as e:
                    pass  # Log in production

            # Sleep for fraction of update interval
            time.sleep(self.config.update_interval_s / 4)

    def reset(self) -> None:
        """Reset all state."""
        with self._lock:
            self._buffer.clear()
            self._mask_buffer.clear()
            self._timestamps.clear()
            self._engine.reset()
            self._latest_result = None
            self._last_update = datetime.now()
            self._samples_since_update = 0
            self._stats = StreamingStats()
            self._state = StreamingState.IDLE

    def get_window_data(self) -> tuple:
        """Get current window data.

        Returns:
            (Y, mask, timestamps) - current window state
        """
        with self._lock:
            if len(self._buffer) == 0:
                return np.array([[]]), np.array([[]]), []

            Y = np.array(list(self._buffer)).T
            mask = np.array(list(self._mask_buffer)).T
            timestamps = list(self._timestamps)

        return Y, mask, timestamps


class AdaptiveStreamingBTF(StreamingBTF):
    """Streaming BTF with adaptive update scheduling.

    Automatically adjusts update frequency based on signal
    dynamics and computational budget.
    """

    def __init__(self,
                 n_signals: int,
                 config: Optional[StreamingConfig] = None,
                 on_update: Optional[Callable[[BTFResult], None]] = None,
                 target_latency_ms: float = 500.0):
        """Initialize adaptive streaming BTF.

        Args:
            n_signals: Number of input signal streams
            config: Base streaming configuration
            on_update: Callback when new BTF result available
            target_latency_ms: Target inference latency
        """
        super().__init__(n_signals, config, on_update)
        self.target_latency_ms = target_latency_ms
        self._coherence_history: deque = deque(maxlen=10)

    def _should_update(self) -> bool:
        """Adaptive update decision based on signal dynamics."""
        # Base check
        if not super()._should_update():
            return False

        # If we have coherence history, adapt based on stability
        if len(self._coherence_history) >= 3:
            coherences = list(self._coherence_history)
            variance = np.var(coherences)

            # High variance = unstable = update more frequently
            # Low variance = stable = can update less
            if variance > 0.1:
                # Unstable: update every half interval
                elapsed = (datetime.now() - self._last_update).total_seconds()
                return elapsed >= self.config.update_interval_s / 2
            elif variance < 0.01:
                # Very stable: can wait longer
                elapsed = (datetime.now() - self._last_update).total_seconds()
                return elapsed >= self.config.update_interval_s * 1.5

        return True

    def _perform_update(self, force_degraded: bool = False) -> BTFResult:
        """Perform update with adaptive iteration count."""
        # Adapt iterations based on recent performance
        if self._stats.total_updates > 3:
            if self._stats.avg_inference_time_ms > self.target_latency_ms:
                # Too slow: reduce iterations
                self._engine.n_iter = max(10, self._engine.n_iter - 5)
            elif self._stats.avg_inference_time_ms < self.target_latency_ms * 0.5:
                # Fast enough: can increase quality
                self._engine.n_iter = min(50, self._engine.n_iter + 2)

        result = super()._perform_update(force_degraded)

        # Track coherence for stability detection
        if result is not None:
            # Compute coherence from result
            coherence = np.mean(result.band_amplitudes)
            self._coherence_history.append(coherence)

        return result


def create_streaming_btf(n_signals: int,
                         window_size: int = 50,
                         update_interval_s: float = 1.0,
                         adaptive: bool = True,
                         on_update: Optional[Callable[[BTFResult], None]] = None) -> StreamingBTF:
    """Factory function to create streaming BTF processor.

    Args:
        n_signals: Number of input signal streams
        window_size: Sliding window size
        update_interval_s: Seconds between updates
        adaptive: Use adaptive scheduling
        on_update: Callback for updates

    Returns:
        Configured StreamingBTF or AdaptiveStreamingBTF
    """
    config = StreamingConfig(
        window_size=window_size,
        update_interval_s=update_interval_s,
        real_time_mode=True,
    )

    if adaptive:
        return AdaptiveStreamingBTF(n_signals, config, on_update)
    else:
        return StreamingBTF(n_signals, config, on_update)
