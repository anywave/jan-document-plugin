"""
SCOUTER: 3-Class Destabilization Classifier.

Classifies coherence perturbations into three destabilization classes
using the Psi Echo Index (autocorrelation of CCS over time):

- Class A (NOISE): Random, transient perturbations — low echo, quick recovery
- Class B (SHADOW): Structured, persistent patterns — high echo, stable physiology
- Class C (TRAUMA): Physiological destabilization — HR instability, entropy rising

The Psi Echo Index measures autocorrelation of the scalar coherence
signal at lags 5-20 samples. High autocorrelation indicates structured
repeating patterns (shadow); low indicates random noise.

(c) 2026 Anywave Creations
MIT License
"""

from collections import deque
from enum import Enum
from typing import Dict, Any

import numpy as np

from .multiwave_state import MultiWaveCoherenceState


class DestabilizationClass(Enum):
    """Classification of coherence destabilization events."""
    STABLE = "STABLE"
    NOISE = "NOISE"       # Class A — transient, random
    SHADOW = "SHADOW"     # Class B — structured, persistent, physiologically stable
    TRAUMA = "TRAUMA"     # Class C — physiological destabilization


class Scouter:
    """3-class destabilization classifier using Psi Echo Index.

    Maintains a rolling buffer of scalar coherence (CCS) values and
    classifies perturbation patterns by their autocorrelation structure,
    duration, and physiological indicators.

    Args:
        buffer_size: Maximum number of CCS samples to retain.
        noise_echo_threshold: Psi echo index below this → NOISE (Class A).
        shadow_echo_threshold: Psi echo index above this → candidate SHADOW.
        shadow_min_duration: Minimum consecutive perturbed samples for SHADOW.
        entropy_spike_threshold: CCS variance rate threshold for entropy detection.
        trauma_rate_threshold: Rate-of-change threshold for trauma escalation.
    """

    def __init__(
        self,
        buffer_size: int = 60,
        noise_echo_threshold: float = 0.3,
        shadow_echo_threshold: float = 0.6,
        shadow_min_duration: int = 20,
        entropy_spike_threshold: float = 0.15,
        trauma_rate_threshold: float = 0.05,
    ):
        self.buffer_size = buffer_size
        self.noise_echo_threshold = noise_echo_threshold
        self.shadow_echo_threshold = shadow_echo_threshold
        self.shadow_min_duration = shadow_min_duration
        self.entropy_spike_threshold = entropy_spike_threshold
        self.trauma_rate_threshold = trauma_rate_threshold

        # State
        self.echo_buffer: deque = deque(maxlen=buffer_size)
        self.psi_echo_index: float = 0.0
        self.confidence: float = 0.0

        # Internals
        self._baseline_ccs: float = 0.0
        self._baseline_count: int = 0
        self._perturbation_duration: int = 0
        self._last_classification: DestabilizationClass = DestabilizationClass.STABLE
        self._entropy_rates: deque = deque(maxlen=30)

    def classify(self, state: MultiWaveCoherenceState) -> DestabilizationClass:
        """Classify the current coherence state.

        Appends scalar_coherence to the echo buffer, updates the baseline
        from healthy readings, computes the Psi Echo Index, then applies
        the 3-class decision logic.

        Args:
            state: Current multi-wave coherence state.

        Returns:
            The destabilization class for this sample.
        """
        ccs = state.scalar_coherence
        self.echo_buffer.append(ccs)

        # Update baseline from healthy readings (CCS > 0.6 and breath entrained)
        # The 0.6 threshold prevents mildly perturbed readings from eroding
        # the baseline, which is critical for accurate perturbation detection.
        if ccs > 0.6 and state.breath_entrained:
            self._baseline_count += 1
            alpha = 1.0 / self._baseline_count
            self._baseline_ccs += alpha * (ccs - self._baseline_ccs)

        # Need minimum samples for meaningful classification
        if len(self.echo_buffer) < 5:
            self._last_classification = DestabilizationClass.STABLE
            self.confidence = 0.0
            return DestabilizationClass.STABLE

        # Compute Psi Echo Index (use perturbation window if active)
        self.psi_echo_index = self._compute_psi_echo_index(
            perturbation_samples=self._perturbation_duration
        )

        # Track entropy rate (variance of recent CCS deltas)
        self._update_entropy_rate()

        # Determine if currently perturbed (CCS below baseline - margin)
        baseline = self._baseline_ccs if self._baseline_ccs > 0 else 0.6
        perturbation_margin = 0.1
        is_perturbed = ccs < (baseline - perturbation_margin)

        if is_perturbed:
            self._perturbation_duration += 1
        else:
            self._perturbation_duration = 0

        # --- Classification logic ---

        # Check TRAUMA first (most urgent)
        trauma_detected = self._check_trauma(state)
        if trauma_detected:
            self.confidence = min(1.0, 0.7 + abs(self.psi_echo_index))
            self._last_classification = DestabilizationClass.TRAUMA
            return DestabilizationClass.TRAUMA

        # Check SHADOW (Class B): structured echo persisting over time
        if (self.psi_echo_index > self.shadow_echo_threshold
                and self._perturbation_duration >= self.shadow_min_duration
                and state.breath_entrained):
            self.confidence = min(1.0, self.psi_echo_index)
            self._last_classification = DestabilizationClass.SHADOW
            return DestabilizationClass.SHADOW

        # Check NOISE (Class A): low echo with recent spike
        if is_perturbed and self.psi_echo_index < self.noise_echo_threshold:
            self.confidence = min(1.0, 0.5 + (self.noise_echo_threshold - self.psi_echo_index))
            self._last_classification = DestabilizationClass.NOISE
            return DestabilizationClass.NOISE

        # No perturbation
        self.confidence = max(0.0, 1.0 - abs(self.psi_echo_index))
        self._last_classification = DestabilizationClass.STABLE
        return DestabilizationClass.STABLE

    def _compute_psi_echo_index(self, perturbation_samples: int = 0) -> float:
        """Compute autocorrelation of echo buffer at lags 5-20, averaged.

        The Psi Echo Index measures how much the CCS signal repeats
        itself at medium time lags. High values indicate structured
        oscillation patterns (shadow); low values indicate noise.

        When perturbation is active, focuses on the perturbed region
        to avoid baseline dilution. Requires a minimum of 5 overlapping
        pairs per lag for statistical reliability.

        Args:
            perturbation_samples: Number of recent samples in perturbation.
                If > 10, uses this as the analysis window.

        Returns:
            RMS of autocorrelations across valid lags. Range 0 to 1.
        """
        full_buf = np.array(self.echo_buffer)
        # Use perturbation window if active and large enough,
        # otherwise default to last 30 samples
        if perturbation_samples > 10:
            window = min(perturbation_samples, len(full_buf))
        else:
            window = min(30, len(full_buf))
        buf = full_buf[-window:]
        n = len(buf)

        if n < 6:
            return 0.0

        mean = np.mean(buf)
        var = np.var(buf)

        if var < 1e-12:
            return 0.0

        max_lag = min(20, n - 1)
        min_lag = 5

        if min_lag > max_lag:
            return 0.0

        autocorrs = []
        centered = buf - mean
        min_overlap = 5  # Require at least 5 pairs for reliable estimate

        for lag in range(min_lag, max_lag + 1):
            overlap = n - lag
            if overlap < min_overlap:
                break
            # Autocorrelation at this lag
            ac = np.sum(centered[:overlap] * centered[lag:]) / (overlap * var)
            autocorrs.append(ac)

        if not autocorrs:
            return 0.0

        # Use RMS of autocorrelations to capture both positive and negative
        # structure (e.g., alternating patterns have strong negative autocorr
        # at odd lags but strong positive at even lags — both are structure).
        arr = np.array(autocorrs)
        return float(np.sqrt(np.mean(arr ** 2)))

    def _update_entropy_rate(self) -> None:
        """Track entropy rate as variance of recent CCS deltas."""
        if len(self.echo_buffer) < 2:
            return
        buf = np.array(self.echo_buffer)
        deltas = np.diff(buf[-min(10, len(buf)):])
        if len(deltas) > 0:
            self._entropy_rates.append(float(np.var(deltas)))

    def _check_trauma(self, state: MultiWaveCoherenceState) -> bool:
        """Check for Class C (TRAUMA) indicators.

        Trauma is indicated by:
        - HR instability (breath_entrained=False) combined with deterioration
        - FAST band spike with rising entropy rate

        Args:
            state: Current coherence state.

        Returns:
            True if trauma pattern detected.
        """
        # HR instability: breath not entrained AND coherence dropping
        hr_unstable = not state.breath_entrained

        # FAST band spike: index 3 significantly elevated relative to CORE (index 2)
        fast_amp = float(state.band_amplitudes[3])
        core_amp = float(state.band_amplitudes[2])
        fast_spike = fast_amp > core_amp * 1.5

        # Rising entropy rate
        entropy_rising = False
        if len(self._entropy_rates) >= 3:
            recent = list(self._entropy_rates)[-3:]
            # Check if entropy is above threshold and trending up
            if recent[-1] > self.entropy_spike_threshold:
                entropy_rising = True
            elif len(recent) >= 2 and all(
                recent[i] > recent[i - 1] for i in range(1, len(recent))
            ):
                entropy_rising = recent[-1] > self.trauma_rate_threshold

        # CCS deteriorating (well below baseline)
        baseline = self._baseline_ccs if self._baseline_ccs > 0 else 0.6
        ccs = float(self.echo_buffer[-1])
        ccs_low = ccs < baseline * 0.6

        # Decision: HR unstable with CCS dropping, or FAST spike with entropy
        if hr_unstable and ccs_low:
            return True
        if fast_spike and entropy_rising:
            return True

        return False

    def get_status(self) -> Dict[str, Any]:
        """Get current scouter status.

        Returns:
            Dictionary with classification, psi_echo_index, confidence,
            baseline_ccs, and buffer_length.
        """
        return {
            'classification': self._last_classification.value,
            'psi_echo_index': self.psi_echo_index,
            'confidence': self.confidence,
            'baseline_ccs': self._baseline_ccs,
            'buffer_length': len(self.echo_buffer),
        }

    def reset(self) -> None:
        """Reset all scouter state."""
        self.echo_buffer.clear()
        self.psi_echo_index = 0.0
        self.confidence = 0.0
        self._baseline_ccs = 0.0
        self._baseline_count = 0
        self._perturbation_duration = 0
        self._last_classification = DestabilizationClass.STABLE
        self._entropy_rates.clear()
