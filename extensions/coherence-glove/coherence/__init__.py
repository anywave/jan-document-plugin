"""
Coherence module for multi-wave coherence analysis.

This module provides the core coherence computation pipeline:
- MultiWaveCoherenceState: Central state representation
- Scalar coherence reduction from band data
- BTF (Bayesian Temporal Factorization) inference
- Integration with ACSP consent determination

(c) 2026 Anywave Creations
MIT License
"""

from .multiwave_state import (
    MultiWaveCoherenceState,
    BAND_ORDER,
)

from .scalar_reduction import (
    compute_scalar_coherence,
    compute_phase_coherence,
    compute_amplitude_factor,
    compute_uncertainty,
    coherence_to_consent_level,
    select_reference_phase,
    get_phi_weights,
)

from .btf_engine import (
    BTFEngine,
    BTFResult,
    create_btf_engine,
)

from .streaming_btf import (
    StreamingBTF,
    AdaptiveStreamingBTF,
    StreamingConfig,
    StreamingState,
    StreamingStats,
    create_streaming_btf,
)

from .acsp_adapter import (
    ACSPSignal,
    ConsentResult,
    CoherenceToACSPAdapter,
    StreamingConsentTracker,
    create_acsp_adapter,
    create_consent_tracker,
    # Re-export consent states for convenience
    FULL_CONSENT,
    ATTENTIVE,
    DIMINISHED_CONSENT,
    SUSPENDED_CONSENT,
    EMERGENCY_OVERRIDE,
)

from .crisis_detection import (
    CrisisType,
    CrisisSeverity,
    CrisisThresholds,
    CrisisEvent,
    CrisisHistory,
    CrisisDetector,
    create_crisis_detector,
)

__all__ = [
    # State
    'MultiWaveCoherenceState',
    'BAND_ORDER',
    # Scalar reduction
    'compute_scalar_coherence',
    'compute_phase_coherence',
    'compute_amplitude_factor',
    'compute_uncertainty',
    'coherence_to_consent_level',
    'select_reference_phase',
    'get_phi_weights',
    # BTF inference
    'BTFEngine',
    'BTFResult',
    'create_btf_engine',
    # Streaming BTF
    'StreamingBTF',
    'AdaptiveStreamingBTF',
    'StreamingConfig',
    'StreamingState',
    'StreamingStats',
    'create_streaming_btf',
    # ACSP Integration
    'ACSPSignal',
    'ConsentResult',
    'CoherenceToACSPAdapter',
    'StreamingConsentTracker',
    'create_acsp_adapter',
    'create_consent_tracker',
    'FULL_CONSENT',
    'ATTENTIVE',
    'DIMINISHED_CONSENT',
    'SUSPENDED_CONSENT',
    'EMERGENCY_OVERRIDE',
    # Crisis Detection
    'CrisisType',
    'CrisisSeverity',
    'CrisisThresholds',
    'CrisisEvent',
    'CrisisHistory',
    'CrisisDetector',
    'create_crisis_detector',
]

__version__ = '0.1.0'
