"""QSE Engine — orchestrates 7 validation modules sequentially."""
from __future__ import annotations
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from models.state import QSEState, QSEInputs, QSEVerdict, ModuleResult, Flag
from .breath_symmetry import BreathSymmetryModule
from .emotional_tone import EmotionalToneModule
from .identity_mirror import IdentityMirrorModule
from .resonance import ResonanceModule, SIGMA_R_THRESHOLD
from .amplification import AmplificationModule
from .coercion import CoercionModule
from .integration import IntegrationModule

log = logging.getLogger('qse')


class QSEEngine:
    """
    Quantum Symbol Engine — 7-module coherence validation pipeline.

    Modules run sequentially. If any module raises a critical flag,
    the pipeline halts early. The overall verdict is based on Σᵣ ≥ 0.88.
    """

    def __init__(self):
        self.modules = [
            BreathSymmetryModule(),
            EmotionalToneModule(),
            IdentityMirrorModule(),
            ResonanceModule(),
            AmplificationModule(),
            CoercionModule(),
            IntegrationModule(),
        ]
        self.state = QSEState()
        self._coherence_state: Optional[Dict[str, Any]] = None

    def set_coherence_state(self, state: Dict[str, Any]):
        """Update cached coherence engine state (from coherence-glove relay)."""
        self._coherence_state = state

    def validate_field(self, inputs: QSEInputs) -> QSEVerdict:
        """
        Run full 7-module validation pipeline.

        Each module returns ModuleResult(passed, score, flags).
        If any module produces a critical flag, pipeline halts early.
        Overall verdict: Σᵣ ≥ 0.88 → COHERENCE UNION VERIFIED.
        """
        results: list[ModuleResult] = []
        coherence = inputs.coherence_state or self._coherence_state

        for module in self.modules:
            try:
                result = self._run_module(module, inputs, coherence, results)
            except Exception as e:
                log.error(f'Module {module.name} error: {e}')
                result = ModuleResult(
                    module=module.name, passed=False, score=0.0,
                    flags=[Flag('module_error', 'critical', str(e))],
                )

            results.append(result)

            # Halt on critical flags
            if result.flags and any(f.severity == 'critical' for f in result.flags):
                log.info(f'Pipeline halted at {module.name} (critical flag)')
                verdict = QSEVerdict(
                    passed=False,
                    sigma_r=self._compute_resonance(results),
                    halted_at=module.name,
                    results=results,
                    verdict=f'HALTED AT {module.name.upper()}',
                )
                self._update_state(verdict)
                return verdict

        # All modules ran — compute final Σᵣ
        sigma_r = self._compute_resonance(results)
        passed = sigma_r >= SIGMA_R_THRESHOLD

        verdict = QSEVerdict(
            passed=passed,
            sigma_r=sigma_r,
            results=results,
            verdict='COHERENCE UNION VERIFIED' if passed else 'PHASE MISMATCH',
        )
        self._update_state(verdict)
        return verdict

    def _run_module(self, module, inputs: QSEInputs,
                    coherence: Optional[dict],
                    prior_results: list) -> ModuleResult:
        """Dispatch to the appropriate module with the right inputs."""
        name = module.name

        if name == 'breath_symmetry':
            return module.evaluate(
                inputs.breath_waveform_1, inputs.breath_waveform_2, coherence)
        elif name == 'emotional_tone':
            return module.evaluate(inputs.emotional_tokens, coherence)
        elif name == 'identity_mirror':
            return module.evaluate(inputs.identity_assertions, coherence)
        elif name == 'resonance':
            prior_scores = [r.score for r in prior_results] if prior_results else None
            return module.evaluate(inputs.signal_metrics, coherence, prior_scores)
        elif name == 'amplification':
            return module.evaluate(inputs.field_energy_history, coherence)
        elif name == 'coercion':
            return module.evaluate(inputs.signal_text, inputs.context, coherence)
        elif name == 'integration':
            return module.evaluate(inputs.session_data, coherence, prior_results)
        else:
            return ModuleResult(module=name, passed=True, score=0.5)

    def _compute_resonance(self, results: list[ModuleResult]) -> float:
        """
        Compute Σᵣ from module results.
        Weighted average of module scores with early modules weighted higher.
        """
        if not results:
            return 0.0

        # Weights: breath and resonance are most important
        weights = {
            'breath_symmetry': 0.20,
            'emotional_tone': 0.15,
            'identity_mirror': 0.10,
            'resonance': 0.20,
            'amplification': 0.15,
            'coercion': 0.10,
            'integration': 0.10,
        }

        total_weight = 0.0
        total_value = 0.0
        for r in results:
            w = weights.get(r.module, 0.1)
            total_weight += w
            total_value += r.score * w

        return total_value / total_weight if total_weight > 0 else 0.0

    def _update_state(self, verdict: QSEVerdict):
        """Update engine state after validation."""
        self.state.last_verdict = verdict
        self.state.validation_count += 1
        self.state.last_update = datetime.now()

        # Update field phase based on verdict
        if verdict.passed:
            self.state.field_phase = 'active'
        elif verdict.halted_at:
            self.state.field_phase = 'disrupted'
        elif verdict.sigma_r >= 0.5:
            self.state.field_phase = 'rising'
        else:
            self.state.field_phase = 'dormant'

    def get_state(self) -> Dict[str, Any]:
        """Return current engine state as dict."""
        return self.state.to_dict()

    def run_single_module(self, module_name: str, inputs: QSEInputs) -> Optional[ModuleResult]:
        """Run a single named module and return its result."""
        coherence = inputs.coherence_state or self._coherence_state
        for module in self.modules:
            if module.name == module_name:
                return self._run_module(module, inputs, coherence, [])
        return None
