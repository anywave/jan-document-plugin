"""Module 5: Amplification — C_amp — field will amplify not deplete."""
from __future__ import annotations
from typing import List, Optional
from models.state import ModuleResult, Flag


class AmplificationModule:
    """
    Validates that the coherence field is amplifying (gaining energy)
    rather than depleting (losing energy). C_amp > 0 means the field
    is a coherence amplifier — SNR improves via feedback.
    """

    name = 'amplification'

    def evaluate(self, field_energy_history: Optional[List[float]] = None,
                 coherence_state: Optional[dict] = None) -> ModuleResult:
        """
        Check field energy trend: is it rising (amplifying) or falling (depleting)?

        C_amp = slope of energy over recent window.
        Positive = amplifying. Negative = depleting.
        """
        flags = []

        if field_energy_history and len(field_energy_history) >= 3:
            # Compute trend via simple linear regression slope
            n = len(field_energy_history)
            x = list(range(n))
            x_mean = sum(x) / n
            y_mean = sum(field_energy_history) / n

            num = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, field_energy_history))
            den = sum((xi - x_mean) ** 2 for xi in x)
            slope = num / den if den > 0 else 0.0

            # Normalize slope to [-1, 1] range
            # A slope of 0.1 per step is considered strongly positive
            c_amp = max(-1.0, min(1.0, slope * 10.0))

            # Map c_amp to score [0, 1]
            score = (c_amp + 1.0) / 2.0

            if c_amp < -0.3:
                flags.append(Flag('field_depleting', 'warning',
                                  f'Field energy declining: C_amp = {c_amp:.3f}'))
            if c_amp < -0.7:
                flags.append(Flag('severe_depletion', 'critical',
                                  'Severe field depletion — interaction may be extractive'))

        elif coherence_state:
            # Fallback: use scalar coherence as proxy
            sc = coherence_state.get('scalarCoherence', 0.0)
            score = sc  # Direct mapping
            c_amp = (sc - 0.5) * 2.0  # Center around 0

        else:
            # No data — neutral
            score = 0.5
            c_amp = 0.0

        passed = score >= 0.4  # Allow slight depletion, fail on strong

        return ModuleResult(
            module=self.name, passed=passed, score=score,
            flags=flags,
            details={
                'c_amp': c_amp if 'c_amp' in dir() else 0.0,
                'trend': 'amplifying' if score > 0.5 else 'depleting' if score < 0.4 else 'stable',
                'history_length': len(field_energy_history) if field_energy_history else 0,
            },
        )
