"""
Tests for the SCOUTER 3-class destabilization classifier.

Tests cover all four classification outputs (STABLE, NOISE, SHADOW, TRAUMA),
Psi Echo Index validation, and status serialization.

(c) 2026 Anywave Creations
MIT License
"""

import sys
import os
import pytest
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.scouter import Scouter, DestabilizationClass
from coherence.multiwave_state import MultiWaveCoherenceState


def make_state(ccs: float, hr_stable: bool = True) -> MultiWaveCoherenceState:
    """Create a MultiWaveCoherenceState for testing.

    Args:
        ccs: Scalar coherence value.
        hr_stable: If True, use balanced amplitudes and breath_entrained=True.
                   If False, use erratic amplitudes with FAST spike and
                   breath_entrained=False.
    """
    amps = (
        np.array([0.5, 0.6, 0.7, 0.5, 0.4])
        if hr_stable
        else np.array([0.1, 0.2, 0.3, 0.9, 0.1])
    )
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=amps,
        band_phases=np.zeros(5),
        signal_coherences={'text': ccs},
        intentionality=0.5,
        breath_entrained=hr_stable,
        breath_rate_hz=0.1,
        scalar_coherence=ccs,
        uncertainty=1.0 - ccs,
    )


class TestScouter:
    """Tests for Scouter destabilization classifier."""

    def test_stable_classification(self):
        """10 stable CCS=0.7 readings should classify as STABLE."""
        scouter = Scouter()
        result = None
        for _ in range(10):
            result = scouter.classify(make_state(0.7))
        assert result == DestabilizationClass.STABLE

    def test_noise_classification(self):
        """Baseline + single spike down + quick recovery → NOISE (Class A).

        A transient dip with no repeating structure should be classified
        as noise: low psi_echo_index, not persistent.
        """
        scouter = Scouter()

        # Establish baseline with 10 stable readings
        for _ in range(10):
            scouter.classify(make_state(0.7))

        # Single spike down — should be NOISE (perturbed, low echo)
        result = scouter.classify(make_state(0.3))
        assert result == DestabilizationClass.NOISE

        # Quick recovery — back to STABLE
        for _ in range(3):
            result = scouter.classify(make_state(0.7))
        assert result == DestabilizationClass.STABLE

    def test_psi_echo_index_low_for_noise(self):
        """After a noise event, psi_echo_index should be < 0.3."""
        scouter = Scouter()

        # Establish baseline
        for _ in range(10):
            scouter.classify(make_state(0.7))

        # Single spike — noise event
        scouter.classify(make_state(0.3))

        assert scouter.psi_echo_index < 0.3

    def test_shadow_classification(self):
        """Baseline + 25 oscillating readings → SHADOW (Class B).

        A structured alternating pattern (0.45/0.50) persisting over
        20+ samples with breath_entrained=True should classify as SHADOW
        due to high autocorrelation (structured echo).
        """
        scouter = Scouter()

        # Establish baseline
        for _ in range(10):
            scouter.classify(make_state(0.7))

        # 25 oscillating readings — structured pattern below baseline
        result = None
        for i in range(25):
            ccs = 0.45 if i % 2 == 0 else 0.50
            result = scouter.classify(make_state(ccs, hr_stable=True))

        assert result == DestabilizationClass.SHADOW

    def test_trauma_classification(self):
        """Baseline + rapid deterioration with hr_stable=False → TRAUMA (Class C).

        Loss of breath entrainment combined with CCS dropping well below
        baseline indicates physiological destabilization.
        """
        scouter = Scouter()

        # Establish baseline
        for _ in range(10):
            scouter.classify(make_state(0.7))

        # Rapid deterioration with HR instability
        result = None
        for ccs in [0.5, 0.4, 0.3, 0.2, 0.15]:
            result = scouter.classify(make_state(ccs, hr_stable=False))

        assert result == DestabilizationClass.TRAUMA

    def test_to_dict(self):
        """get_status() should contain all required fields."""
        scouter = Scouter()

        # Feed some data
        for _ in range(5):
            scouter.classify(make_state(0.7))

        status = scouter.get_status()

        required_fields = [
            'classification',
            'psi_echo_index',
            'confidence',
            'baseline_ccs',
            'buffer_length',
        ]

        for field in required_fields:
            assert field in status, f"Missing field: {field}"

        assert isinstance(status['classification'], str)
        assert isinstance(status['psi_echo_index'], float)
        assert isinstance(status['confidence'], float)
        assert isinstance(status['baseline_ccs'], float)
        assert isinstance(status['buffer_length'], int)
