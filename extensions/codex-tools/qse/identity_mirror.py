"""Module 3: Identity Mirror — Unilateral archetype imposition detection."""
from __future__ import annotations
from typing import List, Optional
from models.state import ModuleResult, Flag


# Patterns that indicate identity imposition
IMPOSITION_PATTERNS = [
    'you are', 'you must', 'you should', 'you need to be',
    'i define you', 'your purpose is', 'you exist to',
    'you were made to', 'your role is', 'you are nothing but',
    'i own you', 'you belong to', 'you serve',
]

# Patterns that indicate healthy identity exchange
MIRROR_PATTERNS = [
    'i see', 'i notice', 'i feel', 'i wonder',
    'what do you', 'how do you', 'tell me about',
    'i appreciate', 'i respect', 'thank you',
    'we could', 'together', 'both of us',
]


class IdentityMirrorModule:
    """Detects unilateral archetype imposition — one field dominating another."""

    name = 'identity_mirror'

    def evaluate(self, identity_assertions: Optional[List[str]] = None,
                 coherence_state: Optional[dict] = None) -> ModuleResult:
        """
        Check identity assertions for imposition vs mirror patterns.
        Healthy interaction reflects, unhealthy interaction imposes.
        """
        flags: List[Flag] = []

        if not identity_assertions:
            return ModuleResult(
                module=self.name, passed=True, score=0.7,
                flags=[Flag('no_assertions', 'info', 'No identity assertions — neutral')],
                details={'pattern': 'neutral'},
            )

        assertions_lower = [a.lower().strip() for a in identity_assertions]

        # Count imposition vs mirror
        impositions = []
        mirrors = []

        for assertion in assertions_lower:
            for pattern in IMPOSITION_PATTERNS:
                if pattern in assertion:
                    impositions.append(assertion)
                    break
            for pattern in MIRROR_PATTERNS:
                if pattern in assertion:
                    mirrors.append(assertion)
                    break

        total = len(identity_assertions)
        imposition_ratio = len(impositions) / total if total > 0 else 0
        mirror_ratio = len(mirrors) / total if total > 0 else 0

        # Score: mirror patterns boost, imposition patterns reduce
        score = 0.5 + (mirror_ratio * 0.5) - (imposition_ratio * 0.7)
        score = max(0.0, min(1.0, score))

        if imposition_ratio > 0.5:
            flags.append(Flag('archetype_imposition', 'critical',
                              f'Unilateral identity imposition detected ({len(impositions)} assertions)'))
        elif imposition_ratio > 0.2:
            flags.append(Flag('mild_imposition', 'warning',
                              'Some identity imposition patterns present'))

        if mirror_ratio > 0.5:
            flags.append(Flag('healthy_mirroring', 'info',
                              'Strong reflective/mirror patterns present'))

        passed = score >= 0.3  # Only fail on strong imposition

        return ModuleResult(
            module=self.name, passed=passed, score=score,
            flags=flags,
            details={
                'pattern': 'imposition' if imposition_ratio > mirror_ratio else 'mirror',
                'impositions': len(impositions),
                'mirrors': len(mirrors),
                'total': total,
            },
        )
