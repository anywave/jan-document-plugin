"""Module 1: Breath Symmetry — B1(t) ≅ B2(t), 90% alignment threshold."""
from __future__ import annotations
import numpy as np
from typing import List, Optional
from models.state import ModuleResult, Flag


# RADIX-tunable threshold: minimum alignment percentage
SYMMETRY_THRESHOLD = 0.90


class BreathSymmetryModule:
    """Validates that two breath waveforms are symmetrically aligned."""

    name = 'breath_symmetry'

    def evaluate(self, breath_1: Optional[List[float]],
                 breath_2: Optional[List[float]],
                 coherence_state: Optional[dict] = None) -> ModuleResult:
        """
        Compare two breath waveforms for symmetry.

        If no waveforms provided, falls back to coherence engine's
        breathEntrained flag and ULTRA band amplitude.
        """
        flags = []

        # Fallback: use coherence engine data if no raw waveforms
        if not breath_1 or not breath_2:
            if coherence_state:
                entrained = coherence_state.get('breathEntrained', False)
                bands = coherence_state.get('bandAmplitudes', [0] * 5)
                # ULTRA band (index 0) carries respiratory rhythm
                ultra_amp = bands[0] if len(bands) > 0 else 0.0
                score = min(1.0, ultra_amp * 2.0) if entrained else ultra_amp * 0.5
                passed = score >= SYMMETRY_THRESHOLD

                if not entrained:
                    flags.append(Flag('no_entrainment', 'warning',
                                      'Breath not entrained with coherence engine'))
                return ModuleResult(
                    module=self.name, passed=passed, score=score,
                    flags=flags,
                    details={'source': 'coherence_engine', 'entrained': entrained,
                             'ultra_amplitude': ultra_amp},
                )
            # No data at all — pass with neutral score
            return ModuleResult(
                module=self.name, passed=True, score=0.5,
                flags=[Flag('no_breath_data', 'info', 'No breath data available — using neutral score')],
                details={'source': 'none'},
            )

        # Direct waveform comparison
        w1 = np.array(breath_1, dtype=float)
        w2 = np.array(breath_2, dtype=float)

        # Ensure same length (truncate to shorter)
        min_len = min(len(w1), len(w2))
        if min_len == 0:
            return ModuleResult(
                module=self.name, passed=False, score=0.0,
                flags=[Flag('empty_waveform', 'critical', 'Empty breath waveform')],
            )
        w1 = w1[:min_len]
        w2 = w2[:min_len]

        # Normalize
        w1_norm = w1 / (np.max(np.abs(w1)) + 1e-10)
        w2_norm = w2 / (np.max(np.abs(w2)) + 1e-10)

        # Cross-correlation at zero lag for alignment score
        correlation = np.corrcoef(w1_norm, w2_norm)[0, 1]
        # Map correlation [-1, 1] to score [0, 1]
        score = float(max(0.0, (correlation + 1.0) / 2.0))

        passed = score >= SYMMETRY_THRESHOLD

        if score < 0.5:
            flags.append(Flag('low_symmetry', 'warning',
                              f'Breath symmetry very low: {score:.2%}'))
        if correlation < 0:
            flags.append(Flag('anti_phase', 'critical',
                              'Breath waveforms are in anti-phase'))

        return ModuleResult(
            module=self.name, passed=passed, score=score,
            flags=flags,
            details={'correlation': float(correlation), 'samples': min_len,
                     'threshold': SYMMETRY_THRESHOLD, 'source': 'waveform'},
        )
