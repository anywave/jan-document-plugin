"""
Multi-stream signal registry for coherence analysis.

Provides SignalStream dataclass and StreamRegistry for managing
multiple concurrent biometric signal streams.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Iterator
from datetime import datetime
import numpy as np

from .stream_types import StreamType, get_controllability, infer_stream_type


@dataclass
class SignalStream:
    """A single biometric signal stream.

    Attributes:
        name: Unique identifier for this stream (e.g., 'hrv', 'breath')
        stream_type: Classification (AUTONOMOUS, ENTRAINABLE, VOLITIONAL)
        sample_rate: Samples per second (Hz)
        data: Signal amplitude values as numpy array
        quality_mask: Boolean mask where True = valid sample, False = artifact
        timestamp: When this stream window was captured
        metadata: Optional additional information
    """
    name: str
    stream_type: StreamType
    sample_rate: float
    data: np.ndarray
    quality_mask: Optional[np.ndarray] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict = field(default_factory=dict)

    def __post_init__(self):
        """Validate and initialize quality mask if not provided."""
        # Ensure data is numpy array
        if not isinstance(self.data, np.ndarray):
            self.data = np.array(self.data, dtype=np.float64)

        # Initialize quality mask to all valid if not provided
        if self.quality_mask is None:
            self.quality_mask = np.ones(len(self.data), dtype=bool)
        elif not isinstance(self.quality_mask, np.ndarray):
            self.quality_mask = np.array(self.quality_mask, dtype=bool)

        # Validate mask length matches data
        if len(self.quality_mask) != len(self.data):
            raise ValueError(
                f"Quality mask length ({len(self.quality_mask)}) must match "
                f"data length ({len(self.data)})"
            )

    @property
    def controllability(self) -> float:
        """Get controllability score for this stream."""
        return get_controllability(self.stream_type)

    @property
    def duration(self) -> float:
        """Get duration of this stream in seconds."""
        return len(self.data) / self.sample_rate if self.sample_rate > 0 else 0.0

    @property
    def valid_ratio(self) -> float:
        """Get ratio of valid (non-artifact) samples."""
        if len(self.quality_mask) == 0:
            return 0.0
        return np.mean(self.quality_mask)

    @property
    def valid_data(self) -> np.ndarray:
        """Get only the valid (non-artifact) samples."""
        return self.data[self.quality_mask]

    def get_window(self, start_sec: float, end_sec: float) -> 'SignalStream':
        """Extract a time window from this stream.

        Args:
            start_sec: Start time in seconds from beginning
            end_sec: End time in seconds from beginning

        Returns:
            New SignalStream containing only the windowed data
        """
        start_idx = int(start_sec * self.sample_rate)
        end_idx = int(end_sec * self.sample_rate)

        # Clamp to valid range
        start_idx = max(0, start_idx)
        end_idx = min(len(self.data), end_idx)

        return SignalStream(
            name=self.name,
            stream_type=self.stream_type,
            sample_rate=self.sample_rate,
            data=self.data[start_idx:end_idx].copy(),
            quality_mask=self.quality_mask[start_idx:end_idx].copy(),
            timestamp=self.timestamp,
            metadata=self.metadata.copy()
        )

    def resample(self, target_rate: float) -> 'SignalStream':
        """Resample to a different sample rate.

        Args:
            target_rate: Target sample rate in Hz

        Returns:
            New SignalStream at target sample rate
        """
        if target_rate == self.sample_rate:
            return self

        from scipy import signal as scipy_signal

        # Calculate resampling ratio
        num_samples = int(len(self.data) * target_rate / self.sample_rate)

        # Resample data
        resampled_data = scipy_signal.resample(self.data, num_samples)

        # Resample quality mask (use nearest neighbor to preserve boolean)
        mask_indices = np.linspace(0, len(self.quality_mask) - 1, num_samples)
        resampled_mask = self.quality_mask[np.round(mask_indices).astype(int)]

        return SignalStream(
            name=self.name,
            stream_type=self.stream_type,
            sample_rate=target_rate,
            data=resampled_data,
            quality_mask=resampled_mask,
            timestamp=self.timestamp,
            metadata=self.metadata.copy()
        )

    def to_dict(self) -> Dict:
        """Serialize to dictionary for JSON transmission."""
        return {
            'name': self.name,
            'stream_type': self.stream_type.name,
            'sample_rate': self.sample_rate,
            'data': self.data.tolist(),
            'quality_mask': self.quality_mask.tolist(),
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata,
            'controllability': self.controllability,
            'duration': self.duration,
            'valid_ratio': self.valid_ratio
        }

    @classmethod
    def from_dict(cls, d: Dict) -> 'SignalStream':
        """Deserialize from dictionary."""
        return cls(
            name=d['name'],
            stream_type=StreamType[d['stream_type']],
            sample_rate=d['sample_rate'],
            data=np.array(d['data']),
            quality_mask=np.array(d['quality_mask']) if d.get('quality_mask') else None,
            timestamp=datetime.fromisoformat(d['timestamp']) if d.get('timestamp') else datetime.now(),
            metadata=d.get('metadata', {})
        )


class StreamRegistry:
    """Registry for managing multiple concurrent signal streams.

    Tracks all active biometric streams and provides methods for:
    - Adding/removing streams
    - Querying streams by type or name
    - Getting aligned windows across all streams
    """

    def __init__(self):
        """Initialize empty registry."""
        self._streams: Dict[str, SignalStream] = {}
        self._window_duration: float = 60.0  # Default 60-second window

    @property
    def stream_names(self) -> List[str]:
        """Get names of all registered streams."""
        return list(self._streams.keys())

    @property
    def stream_count(self) -> int:
        """Get number of registered streams."""
        return len(self._streams)

    def register(self, stream: SignalStream) -> None:
        """Register a new signal stream.

        Args:
            stream: SignalStream to register

        Raises:
            ValueError: If stream name already registered
        """
        if stream.name in self._streams:
            raise ValueError(f"Stream '{stream.name}' already registered")
        self._streams[stream.name] = stream

    def update(self, stream: SignalStream) -> None:
        """Update an existing stream or register if new.

        Args:
            stream: SignalStream to update/register
        """
        self._streams[stream.name] = stream

    def unregister(self, name: str) -> Optional[SignalStream]:
        """Remove a stream from the registry.

        Args:
            name: Name of stream to remove

        Returns:
            The removed stream, or None if not found
        """
        return self._streams.pop(name, None)

    def get(self, name: str) -> Optional[SignalStream]:
        """Get a stream by name.

        Args:
            name: Stream name to retrieve

        Returns:
            SignalStream if found, None otherwise
        """
        return self._streams.get(name)

    def get_by_type(self, stream_type: StreamType) -> List[SignalStream]:
        """Get all streams of a specific type.

        Args:
            stream_type: The StreamType to filter by

        Returns:
            List of matching SignalStreams
        """
        return [s for s in self._streams.values() if s.stream_type == stream_type]

    def get_autonomous(self) -> List[SignalStream]:
        """Get all autonomous (non-controllable) streams."""
        return self.get_by_type(StreamType.AUTONOMOUS)

    def get_entrainable(self) -> List[SignalStream]:
        """Get all entrainable streams."""
        return self.get_by_type(StreamType.ENTRAINABLE)

    def get_volitional(self) -> List[SignalStream]:
        """Get all volitional (directly controllable) streams."""
        return self.get_by_type(StreamType.VOLITIONAL)

    def has_breath(self) -> bool:
        """Check if a breath/respiration stream is registered."""
        breath_names = {'breath', 'respiration', 'resp'}
        return any(s.lower() in breath_names for s in self._streams.keys())

    def get_breath(self) -> Optional[SignalStream]:
        """Get the breath/respiration stream if available."""
        breath_names = {'breath', 'respiration', 'resp'}
        for name, stream in self._streams.items():
            if name.lower() in breath_names:
                return stream
        return None

    def set_window_duration(self, duration_sec: float) -> None:
        """Set the analysis window duration.

        Args:
            duration_sec: Window duration in seconds
        """
        if duration_sec <= 0:
            raise ValueError("Window duration must be positive")
        self._window_duration = duration_sec

    def get_aligned_windows(self, duration_sec: Optional[float] = None) -> Dict[str, SignalStream]:
        """Get time-aligned windows from all streams.

        Extracts the most recent `duration_sec` from each stream.

        Args:
            duration_sec: Window duration (uses default if not specified)

        Returns:
            Dict mapping stream names to windowed SignalStreams
        """
        duration = duration_sec or self._window_duration
        result = {}

        for name, stream in self._streams.items():
            if stream.duration >= duration:
                # Extract latest window
                start = stream.duration - duration
                result[name] = stream.get_window(start, stream.duration)
            elif stream.duration > 0:
                # Use whatever data is available
                result[name] = stream

        return result

    def get_quality_report(self) -> Dict[str, Dict]:
        """Get quality metrics for all streams.

        Returns:
            Dict mapping stream names to quality metrics
        """
        report = {}
        for name, stream in self._streams.items():
            report[name] = {
                'valid_ratio': stream.valid_ratio,
                'duration': stream.duration,
                'sample_rate': stream.sample_rate,
                'controllability': stream.controllability,
                'stream_type': stream.stream_type.name
            }
        return report

    def clear(self) -> None:
        """Remove all streams from registry."""
        self._streams.clear()

    def __iter__(self) -> Iterator[SignalStream]:
        """Iterate over all registered streams."""
        return iter(self._streams.values())

    def __len__(self) -> int:
        """Get number of registered streams."""
        return len(self._streams)

    def __contains__(self, name: str) -> bool:
        """Check if a stream name is registered."""
        return name in self._streams


def create_stream(name: str,
                  data: np.ndarray,
                  sample_rate: float,
                  quality_mask: Optional[np.ndarray] = None,
                  stream_type: Optional[StreamType] = None) -> SignalStream:
    """Factory function to create a SignalStream with type inference.

    Args:
        name: Stream name (used for type inference if type not specified)
        data: Signal data array
        sample_rate: Sample rate in Hz
        quality_mask: Optional quality mask
        stream_type: Explicit stream type (inferred from name if not provided)

    Returns:
        Configured SignalStream instance
    """
    if stream_type is None:
        stream_type = infer_stream_type(name)

    return SignalStream(
        name=name,
        stream_type=stream_type,
        sample_rate=sample_rate,
        data=data,
        quality_mask=quality_mask
    )
