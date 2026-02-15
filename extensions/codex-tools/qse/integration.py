"""Module 7: Integration — Afterglow stabilization + memory closure."""
from __future__ import annotations
from typing import Optional, Dict, Any
from models.state import ModuleResult, Flag


class IntegrationModule:
    """
    Final module: ensures the session can close cleanly with
    afterglow stabilization. Memory closure means the field
    state is recorded and can be recalled next session.
    """

    name = 'integration'

    def evaluate(self, session_data: Optional[Dict[str, Any]] = None,
                 coherence_state: Optional[dict] = None,
                 prior_results: Optional[list] = None) -> ModuleResult:
        """
        Assess integration readiness:
        1. Are prior modules mostly passing?
        2. Is the field stable enough to close?
        3. Can memory be cleanly recorded?
        """
        flags = []

        # Check prior module results
        prior_pass_rate = 1.0
        if prior_results:
            passes = sum(1 for r in prior_results if r.passed)
            prior_pass_rate = passes / len(prior_results) if prior_results else 1.0

        # Check coherence stability
        stability = 0.5
        if coherence_state:
            sc = coherence_state.get('scalarCoherence', 0.0)
            active = coherence_state.get('active', False)
            stability = sc if active else 0.3

        # Check session data
        session_clean = True
        if session_data:
            # Look for unresolved flags
            unresolved = session_data.get('unresolved_flags', 0)
            if unresolved > 0:
                session_clean = False
                flags.append(Flag('unresolved_flags', 'warning',
                                  f'{unresolved} unresolved flags from prior modules'))

        # Integration score: weighted combination
        score = (prior_pass_rate * 0.4) + (stability * 0.4) + (0.2 if session_clean else 0.0)
        score = max(0.0, min(1.0, score))

        # Afterglow check: if score >= 0.7, field can stabilize
        afterglow_ready = score >= 0.7

        if afterglow_ready:
            flags.append(Flag('afterglow_ready', 'info',
                              'Field ready for afterglow stabilization'))
        else:
            flags.append(Flag('integration_incomplete', 'warning',
                              'Field not yet stable for clean closure'))

        # Memory closure: can we save state?
        memory_closure = coherence_state is not None and coherence_state.get('active', False)

        passed = score >= 0.5  # Integration is lenient — it's about trend, not threshold

        return ModuleResult(
            module=self.name, passed=passed, score=score,
            flags=flags,
            details={
                'prior_pass_rate': prior_pass_rate,
                'stability': stability,
                'session_clean': session_clean,
                'afterglow_ready': afterglow_ready,
                'memory_closure': memory_closure,
            },
        )
