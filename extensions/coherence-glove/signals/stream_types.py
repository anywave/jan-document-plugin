"""
Signal stream types for multi-stream coherence analysis.

Defines the StreamType enum for classifying biometric signals by controllability.

(c) 2026 Anywave Creations
MIT License
"""

from enum import Enum, auto
from typing import Dict


class StreamType(Enum):
    """Signal stream controllability classification.

    Three categories based on volitional control:

    AUTONOMOUS: Cannot be consciously controlled
        - Heart rate variability (HRV)
        - Galvanic skin response (GSR)
        - Pupil dilation

    ENTRAINABLE: Can be influenced but not directly controlled
        - Heart rate (via breath)
        - Blood pressure (via relaxation)
        - EEG rhythms (via meditation)

    VOLITIONAL: Directly controllable
        - Breath rate and depth
        - Muscle tension
        - Eye movements
    """
    AUTONOMOUS = auto()
    ENTRAINABLE = auto()
    VOLITIONAL = auto()


# Controllability scores per stream type (0 = no control, 1 = full control)
STREAM_CONTROLLABILITY: Dict[StreamType, float] = {
    StreamType.AUTONOMOUS: 0.0,
    StreamType.ENTRAINABLE: 0.5,
    StreamType.VOLITIONAL: 1.0,
}


def get_controllability(stream_type: StreamType) -> float:
    """Get controllability score for a stream type.

    Args:
        stream_type: The StreamType to query

    Returns:
        Controllability score from 0.0 (autonomous) to 1.0 (volitional)
    """
    return STREAM_CONTROLLABILITY.get(stream_type, 0.0)


# Default stream type mappings for common signals
DEFAULT_STREAM_TYPES: Dict[str, StreamType] = {
    # Autonomous signals
    'hrv': StreamType.AUTONOMOUS,
    'gsr': StreamType.AUTONOMOUS,
    'eda': StreamType.AUTONOMOUS,  # Electrodermal activity
    'pupil': StreamType.AUTONOMOUS,
    'skin_temp': StreamType.AUTONOMOUS,

    # Entrainable signals
    'heart_rate': StreamType.ENTRAINABLE,
    'blood_pressure': StreamType.ENTRAINABLE,
    'eeg_alpha': StreamType.ENTRAINABLE,
    'eeg_theta': StreamType.ENTRAINABLE,

    # Volitional signals
    'breath': StreamType.VOLITIONAL,
    'respiration': StreamType.VOLITIONAL,
    'emg': StreamType.VOLITIONAL,  # Electromyography
    'eye_movement': StreamType.VOLITIONAL,
}


def infer_stream_type(signal_name: str) -> StreamType:
    """Infer stream type from signal name.

    Args:
        signal_name: Name of the signal (case-insensitive)

    Returns:
        Inferred StreamType, defaults to AUTONOMOUS if unknown
    """
    normalized = signal_name.lower().strip()
    return DEFAULT_STREAM_TYPES.get(normalized, StreamType.AUTONOMOUS)
