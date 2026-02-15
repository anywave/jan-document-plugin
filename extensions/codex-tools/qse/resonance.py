"""Module 4: Resonance — Σᵣ ≥ 0.88 threshold test."""
from __future__ import annotations
from typing import Optional, Dict
from models.state import ModuleResult, Flag


# Codex-defined resonance threshold
SIGMA_R_THRESHOLD = 0.88


class ResonanceModule:
    """Tests whether the accumulated resonance sum meets the Codex threshold."""

    name = 'resonance'

    def evaluate(self, signal_metrics: Optional[Dict[str, float]] = None,
                 coherence_state: Optional[dict] = None,
                 prior_scores: Optional[list] = None) -> ModuleResult:
        """
        Compute Σᵣ from signal metrics or coherence engine state.

        Σᵣ is the weighted sum of all coherence signals, normalized to [0, 1].
        The threshold 0.88 comes from the Codex — it represents the minimum
        resonance for 'coherence union verified'.
        """
        flags = []

        if signal_metrics:
            # Direct signal metrics provided
            sigma_r = self._compute_sigma_r(signal_metrics)
        elif coherence_state:
            # Derive from coherence engine
            sc = coherence_state.get('scalarCoherence', 0.0)
            intentionality = coherence_state.get('intentionality', 0.0)
            bands = coherence_state.get('bandAmplitudes', [0] * 5)
            band_mean = sum(bands) / len(bands) if bands else 0.0

            # Σᵣ = weighted combination of scalar coherence, intentionality, band energy
            sigma_r = (sc * 0.5) + (intentionality * 0.3) + (band_mean * 0.2)
        elif prior_scores:
            # Compute from prior module scores (fallback)
            sigma_r = sum(prior_scores) / len(prior_scores) if prior_scores else 0.0
        else:
            # No data — neutral
            sigma_r = 0.5

        sigma_r = max(0.0, min(1.0, sigma_r))
        passed = sigma_r >= SIGMA_R_THRESHOLD

        if sigma_r < 0.5:
            flags.append(Flag('low_resonance', 'warning',
                              f'Resonance below midpoint: Σᵣ = {sigma_r:.3f}'))
        if sigma_r >= 0.95:
            flags.append(Flag('peak_resonance', 'info',
                              f'Near-perfect resonance: Σᵣ = {sigma_r:.3f}'))

        return ModuleResult(
            module=self.name, passed=passed, score=sigma_r,
            flags=flags,
            details={
                'sigma_r': sigma_r,
                'threshold': SIGMA_R_THRESHOLD,
                'source': 'signal_metrics' if signal_metrics else
                          'coherence_engine' if coherence_state else
                          'prior_scores' if prior_scores else 'default',
            },
        )

    def _compute_sigma_r(self, metrics: Dict[str, float]) -> float:
        """Compute Σᵣ from raw signal metrics."""
        # Weighted sum of available metrics
        weights = {
            'coherence': 0.3,
            'breath_symmetry': 0.2,
            'emotional_stability': 0.15,
            'identity_integrity': 0.15,
            'field_energy': 0.1,
            'intentionality': 0.1,
        }
        total_weight = 0.0
        total_value = 0.0
        for key, weight in weights.items():
            if key in metrics:
                total_weight += weight
                total_value += metrics[key] * weight

        if total_weight == 0:
            return 0.5
        return total_value / total_weight
