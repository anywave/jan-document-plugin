"""
ACSP Adapter for Multi-Wave Coherence Engine.

Maps coherence state to ACSP consent determination signals,
bridging the φ-band coherence pipeline with the consent state machine.

(c) 2026 Anywave Creations
MIT License
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import numpy as np

from .multiwave_state import MultiWaveCoherenceState


# Try to import ACSP components
try:
    from ..acsp import (
        determine_consent_state as acsp_determine,
        ACSPEngine,
        get_acsp_engine,
        FULL_CONSENT,
        ATTENTIVE,
        DIMINISHED_CONSENT,
        SUSPENDED_CONSENT,
        EMERGENCY_OVERRIDE,
        is_actionable_consent,
        requires_reconfirmation,
    )
    ACSP_AVAILABLE = True
except ImportError:
    # Fallback: try absolute import
    try:
        from acsp import (
            determine_consent_state as acsp_determine,
            ACSPEngine,
            get_acsp_engine,
            FULL_CONSENT,
            ATTENTIVE,
            DIMINISHED_CONSENT,
            SUSPENDED_CONSENT,
            EMERGENCY_OVERRIDE,
            is_actionable_consent,
            requires_reconfirmation,
        )
        ACSP_AVAILABLE = True
    except ImportError:
        ACSP_AVAILABLE = False
        # Define constants locally if ACSP not available
        FULL_CONSENT = "FULL_CONSENT"
        ATTENTIVE = "ATTENTIVE"
        DIMINISHED_CONSENT = "DIMINISHED_CONSENT"
        SUSPENDED_CONSENT = "SUSPENDED_CONSENT"
        EMERGENCY_OVERRIDE = "EMERGENCY_OVERRIDE"


@dataclass
class ACSPSignal:
    """Signal format expected by ACSP engine.

    Attributes:
        stress_level: 0.0 (calm) to 1.0 (extreme stress)
        focus_level: 0.0 (distracted) to 1.0 (fully focused)
        somatic_coherence: 0.0-1.0 for phi-based thresholds
        verbal_signal_strength: 0-3 boost factor
        coherence_score: Raw coherence for completion tracking
    """
    stress_level: float = 0.0
    focus_level: float = 0.5
    somatic_coherence: Optional[float] = None
    verbal_signal_strength: int = 0
    coherence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for ACSP engine."""
        d = {
            'stress_level': self.stress_level,
            'focus_level': self.focus_level,
            'coherence_score': self.coherence_score,
        }
        if self.somatic_coherence is not None:
            d['somatic_coherence'] = self.somatic_coherence
        if self.verbal_signal_strength > 0:
            d['verbal_signal_strength'] = self.verbal_signal_strength
        return d


@dataclass
class ConsentResult:
    """Result of ACSP consent determination.

    Attributes:
        state: Consent state (FULL_CONSENT, etc.)
        coherence_state: Original MultiWaveCoherenceState
        signal: Mapped ACSPSignal used for determination
        actionable: Whether actions can proceed
        needs_reconfirmation: Whether extra confirmation required
        completion_info: Completion tracking data (if ACSPEngine used)
        timestamp: When consent was determined
    """
    state: str
    coherence_state: Optional[MultiWaveCoherenceState] = None
    signal: Optional[ACSPSignal] = None
    actionable: bool = True
    needs_reconfirmation: bool = False
    completion_info: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def is_full(self) -> bool:
        """Check if full consent granted."""
        return self.state == FULL_CONSENT

    def is_suspended(self) -> bool:
        """Check if consent suspended."""
        return self.state in (SUSPENDED_CONSENT, EMERGENCY_OVERRIDE)

    def can_proceed(self, require_full: bool = False) -> bool:
        """Check if operation can proceed.

        Args:
            require_full: If True, only FULL_CONSENT allows proceeding
        """
        if require_full:
            return self.state == FULL_CONSENT
        return self.actionable


class CoherenceToACSPAdapter:
    """Adapter that maps coherence state to ACSP signals.

    The mapping strategy:
    - stress_level = 1.0 - coherence (inverse relationship)
    - focus_level = intentionality
    - somatic_coherence = scalar_coherence (direct mapping)
    - coherence_score = scalar_coherence (for completion tracking)

    Additional modifiers:
    - Breath entrainment can boost focus_level
    - Uncertainty affects stress_level
    - Low phase alignment increases stress
    """

    # Mapping coefficients
    STRESS_COHERENCE_WEIGHT = 0.7   # How much coherence affects stress
    STRESS_UNCERTAINTY_WEIGHT = 0.2  # How much uncertainty affects stress
    STRESS_PHASE_WEIGHT = 0.1        # How much phase misalignment affects stress
    FOCUS_INTENTIONALITY_WEIGHT = 0.8
    FOCUS_BREATH_BOOST = 0.15        # Boost for breath entrainment

    def __init__(self,
                 use_somatic: bool = True,
                 uncertainty_scale: float = 2.0):
        """Initialize adapter.

        Args:
            use_somatic: Use somatic_coherence for phi-based thresholds
            uncertainty_scale: Scale factor for uncertainty contribution
        """
        self.use_somatic = use_somatic
        self.uncertainty_scale = uncertainty_scale

    def map_to_signal(self, state: MultiWaveCoherenceState) -> ACSPSignal:
        """Map coherence state to ACSP signal format.

        Args:
            state: MultiWaveCoherenceState from coherence engine

        Returns:
            ACSPSignal for ACSP consent determination
        """
        # Stress: inverse of coherence, affected by uncertainty and phase
        coherence = state.scalar_coherence
        uncertainty = min(1.0, state.uncertainty * self.uncertainty_scale)
        phase_alignment = state.phase_alignment  # 0-1, higher = better alignment

        stress = (
            self.STRESS_COHERENCE_WEIGHT * (1.0 - coherence) +
            self.STRESS_UNCERTAINTY_WEIGHT * uncertainty +
            self.STRESS_PHASE_WEIGHT * (1.0 - phase_alignment)
        )
        stress = np.clip(stress, 0.0, 1.0)

        # Focus: primarily from intentionality, boosted by breath entrainment
        focus = self.FOCUS_INTENTIONALITY_WEIGHT * state.intentionality
        if state.breath_entrained:
            focus += self.FOCUS_BREATH_BOOST
        focus = np.clip(focus, 0.0, 1.0)

        return ACSPSignal(
            stress_level=float(stress),
            focus_level=float(focus),
            somatic_coherence=float(coherence) if self.use_somatic else None,
            coherence_score=float(coherence),
        )

    def determine_consent(self,
                          state: MultiWaveCoherenceState,
                          use_engine: bool = False,
                          fragment_id: str = "coherence") -> ConsentResult:
        """Determine consent state from coherence.

        Args:
            state: MultiWaveCoherenceState from coherence engine
            use_engine: If True, use ACSPEngine with completion tracking
            fragment_id: Fragment ID for completion tracking

        Returns:
            ConsentResult with consent state and metadata
        """
        signal = self.map_to_signal(state)
        signal_dict = signal.to_dict()

        completion_info = None

        if ACSP_AVAILABLE:
            if use_engine:
                # Use ACSPEngine for completion tracking
                engine = get_acsp_engine(fragment_id)
                result = engine.update_consent_state(signal_dict)
                consent_state = result['current_state']
                completion_info = result if result.get('completion_triggered') else None
            else:
                # Simple determination
                consent_state = acsp_determine(signal_dict)

            actionable = is_actionable_consent(consent_state)
            needs_reconfirm = requires_reconfirmation(consent_state)
        else:
            # Fallback: use coherence thresholds directly
            consent_state = self._fallback_consent(state.scalar_coherence)
            actionable = consent_state not in (SUSPENDED_CONSENT, EMERGENCY_OVERRIDE)
            needs_reconfirm = consent_state in (DIMINISHED_CONSENT, ATTENTIVE)

        return ConsentResult(
            state=consent_state,
            coherence_state=state,
            signal=signal,
            actionable=actionable,
            needs_reconfirmation=needs_reconfirm,
            completion_info=completion_info,
            timestamp=datetime.now(),
        )

    def _fallback_consent(self, coherence: float) -> str:
        """Determine consent from coherence when ACSP unavailable.

        Uses φ-based thresholds:
        - >= 0.618 (φ^-1): FULL_CONSENT
        - >= 0.5: ATTENTIVE
        - >= 0.382 (φ^-2): DIMINISHED_CONSENT
        - >= 0.236 (φ^-3): SUSPENDED_CONSENT
        - < 0.236: EMERGENCY_OVERRIDE
        """
        PHI_INV = 0.618033988749895
        PHI_INV_2 = 0.381966011250105
        PHI_INV_3 = 0.236067977499790

        if coherence >= PHI_INV:
            return FULL_CONSENT
        elif coherence >= 0.5:
            return ATTENTIVE
        elif coherence >= PHI_INV_2:
            return DIMINISHED_CONSENT
        elif coherence >= PHI_INV_3:
            return SUSPENDED_CONSENT
        else:
            return EMERGENCY_OVERRIDE


class StreamingConsentTracker:
    """Track consent state over streaming coherence updates.

    Provides:
    - Hysteresis to prevent rapid state oscillation
    - History tracking for trend analysis
    - State duration tracking
    - Callback on state transitions
    """

    def __init__(self,
                 adapter: Optional[CoherenceToACSPAdapter] = None,
                 hysteresis_s: float = 5.0,
                 history_length: int = 100,
                 on_transition: Optional[Callable[[str, str, ConsentResult], None]] = None):
        """Initialize consent tracker.

        Args:
            adapter: CoherenceToACSPAdapter instance
            hysteresis_s: Minimum seconds before allowing state change
            history_length: Number of consent results to keep in history
            on_transition: Callback(old_state, new_state, result) on transitions
        """
        self.adapter = adapter or CoherenceToACSPAdapter()
        self.hysteresis_s = hysteresis_s
        self.history_length = history_length
        self.on_transition = on_transition

        self._history: list = []
        self._current_state: Optional[str] = None
        self._state_start_time: Optional[datetime] = None
        self._pending_transition: Optional[str] = None
        self._pending_transition_time: Optional[datetime] = None

    @property
    def current_state(self) -> Optional[str]:
        """Current consent state."""
        return self._current_state

    @property
    def state_duration_s(self) -> float:
        """Seconds in current state."""
        if self._state_start_time is None:
            return 0.0
        return (datetime.now() - self._state_start_time).total_seconds()

    @property
    def history(self) -> list:
        """Consent history."""
        return list(self._history)

    def update(self,
               coherence_state: MultiWaveCoherenceState,
               use_engine: bool = False) -> ConsentResult:
        """Update consent tracking with new coherence state.

        Args:
            coherence_state: New coherence state from engine
            use_engine: Use ACSPEngine for completion tracking

        Returns:
            ConsentResult (may differ from raw due to hysteresis)
        """
        result = self.adapter.determine_consent(coherence_state, use_engine)

        # Apply hysteresis
        if self._current_state is None:
            # First update
            self._current_state = result.state
            self._state_start_time = datetime.now()
        elif result.state != self._current_state:
            # Potential transition
            if self._pending_transition == result.state:
                # Same pending transition - check if hysteresis passed
                elapsed = (datetime.now() - self._pending_transition_time).total_seconds()
                if elapsed >= self.hysteresis_s:
                    # Apply transition
                    old_state = self._current_state
                    self._current_state = result.state
                    self._state_start_time = datetime.now()
                    self._pending_transition = None
                    self._pending_transition_time = None

                    # Fire callback
                    if self.on_transition:
                        try:
                            self.on_transition(old_state, result.state, result)
                        except Exception:
                            pass  # Don't let callback errors break tracking
            else:
                # New pending transition
                self._pending_transition = result.state
                self._pending_transition_time = datetime.now()
        else:
            # State unchanged - clear any pending transition
            self._pending_transition = None
            self._pending_transition_time = None

        # Update result state to reflect hysteresis
        result.state = self._current_state

        # Add to history
        self._history.append(result)
        if len(self._history) > self.history_length:
            self._history.pop(0)

        return result

    def get_trend(self, window_n: int = 10) -> Dict[str, Any]:
        """Analyze recent consent trend.

        Args:
            window_n: Number of recent results to analyze

        Returns:
            Dict with trend analysis
        """
        if len(self._history) < 2:
            return {
                'trend': 'insufficient_data',
                'avg_coherence': None,
                'state_distribution': {},
            }

        recent = self._history[-window_n:]

        # State distribution
        state_counts = {}
        coherence_values = []
        for r in recent:
            state_counts[r.state] = state_counts.get(r.state, 0) + 1
            if r.coherence_state:
                coherence_values.append(r.coherence_state.scalar_coherence)

        # Coherence trend
        if len(coherence_values) >= 2:
            first_half = np.mean(coherence_values[:len(coherence_values)//2])
            second_half = np.mean(coherence_values[len(coherence_values)//2:])
            if second_half > first_half + 0.05:
                trend = 'improving'
            elif second_half < first_half - 0.05:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'stable'

        return {
            'trend': trend,
            'avg_coherence': np.mean(coherence_values) if coherence_values else None,
            'state_distribution': state_counts,
            'current_state': self._current_state,
            'state_duration_s': self.state_duration_s,
        }

    def reset(self) -> None:
        """Reset tracking state."""
        self._history.clear()
        self._current_state = None
        self._state_start_time = None
        self._pending_transition = None
        self._pending_transition_time = None


def create_acsp_adapter(use_somatic: bool = True) -> CoherenceToACSPAdapter:
    """Factory function to create ACSP adapter.

    Args:
        use_somatic: Use somatic_coherence for phi-based thresholds

    Returns:
        Configured CoherenceToACSPAdapter
    """
    return CoherenceToACSPAdapter(use_somatic=use_somatic)


def create_consent_tracker(
    hysteresis_s: float = 5.0,
    on_transition: Optional[Callable[[str, str, ConsentResult], None]] = None
) -> StreamingConsentTracker:
    """Factory function to create consent tracker.

    Args:
        hysteresis_s: Minimum seconds before state change
        on_transition: Callback on state transitions

    Returns:
        Configured StreamingConsentTracker
    """
    return StreamingConsentTracker(
        hysteresis_s=hysteresis_s,
        on_transition=on_transition,
    )
