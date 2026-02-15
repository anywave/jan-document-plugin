"""Shared fixtures for coherence engine tests."""
import sys
import os
import pytest
import numpy as np
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coherence.multiwave_state import MultiWaveCoherenceState


@pytest.fixture
def default_state():
    return MultiWaveCoherenceState.create_default()


@pytest.fixture
def healthy_state():
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=np.array([0.6, 0.7, 0.8, 0.65, 0.55]),
        band_phases=np.array([0.1, 0.2, 0.3, 0.4, 0.5]),
        signal_coherences={'text': 0.7, 'breath': 0.8},
        intentionality=0.7,
        breath_entrained=True,
        breath_rate_hz=0.1,
        scalar_coherence=0.72,
        uncertainty=0.15,
    )


@pytest.fixture
def unstable_state():
    return MultiWaveCoherenceState(
        timestamp=datetime.now(),
        band_amplitudes=np.array([0.1, 0.15, 0.2, 0.12, 0.08]),
        band_phases=np.array([1.0, 2.5, 0.3, 4.1, 5.8]),
        signal_coherences={'text': 0.2},
        intentionality=0.1,
        breath_entrained=False,
        breath_rate_hz=0.05,
        scalar_coherence=0.15,
        uncertainty=0.7,
    )
