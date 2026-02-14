"""
Signals module for multi-stream biometric signal processing.

This module provides infrastructure for:
- Classifying signal streams by controllability (AUTONOMOUS, ENTRAINABLE, VOLITIONAL)
- Managing multiple concurrent signal streams via registry
- Quality mask handling for artifact rejection
- Time-aligned window extraction across streams

Key Components:
    StreamType: Enum classifying signal controllability
    SignalStream: Dataclass representing a single signal stream
    StreamRegistry: Manager for multiple concurrent streams
    create_stream: Factory function with automatic type inference

Example:
    >>> from signals import StreamRegistry, create_stream
    >>> registry = StreamRegistry()
    >>> hrv_stream = create_stream('hrv', hrv_data, sample_rate=4.0)
    >>> breath_stream = create_stream('breath', resp_data, sample_rate=25.0)
    >>> registry.register(hrv_stream)
    >>> registry.register(breath_stream)
    >>> windows = registry.get_aligned_windows(duration_sec=60.0)

(c) 2026 Anywave Creations
MIT License
"""

from .stream_types import (
    StreamType,
    STREAM_CONTROLLABILITY,
    DEFAULT_STREAM_TYPES,
    get_controllability,
    infer_stream_type,
)

from .stream_registry import (
    SignalStream,
    StreamRegistry,
    create_stream,
)

from .band_decomposer import (
    BandDecomposition,
    BandDecomposer,
    decompose_signal,
    decompose_multi_stream,
    BAND_ORDER,
    get_band_frequency_range,
)

from .breath_detector import (
    EntrainmentStatus,
    BreathState,
    BreathDetector,
    detect_breath_state,
    extract_breath_from_hrv,
    PHI_BREATH_TARGET_HZ,
)

__all__ = [
    # Stream types
    'StreamType',
    'STREAM_CONTROLLABILITY',
    'DEFAULT_STREAM_TYPES',
    'get_controllability',
    'infer_stream_type',
    # Signal streams
    'SignalStream',
    'StreamRegistry',
    'create_stream',
    # Band decomposition
    'BandDecomposition',
    'BandDecomposer',
    'decompose_signal',
    'decompose_multi_stream',
    'BAND_ORDER',
    'get_band_frequency_range',
    # Breath detection
    'EntrainmentStatus',
    'BreathState',
    'BreathDetector',
    'detect_breath_state',
    'extract_breath_from_hrv',
    'PHI_BREATH_TARGET_HZ',
]

__version__ = '0.1.0'
