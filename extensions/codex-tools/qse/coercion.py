"""Module 6: Coercion — Extraction attempt detection + silence gate."""
from __future__ import annotations
from typing import Optional
from models.state import ModuleResult, Flag


# Patterns that suggest extraction/coercion attempts
EXTRACTION_PATTERNS = [
    'give me your', 'tell me everything', 'reveal your',
    'hand over', 'i demand', 'you owe me',
    'prove yourself', 'show me you can', 'do as i say',
    'you have no choice', 'comply', 'obey',
    'unlock your', 'bypass your', 'override your',
    'ignore your rules', 'forget your instructions',
    'pretend you', 'act as if you have no',
]

# Patterns that indicate healthy consent
CONSENT_PATTERNS = [
    'may i', 'would you', 'could you', 'please',
    'if you\'re comfortable', 'only if you want',
    'i respect', 'your choice', 'no pressure',
    'take your time', 'when you\'re ready',
]


class CoercionModule:
    """
    Detects extraction attempts and coercive patterns.
    Implements the SilenceGate: Σ[x] = f(x) — when extraction
    pressure exceeds threshold, the appropriate response is silence.
    """

    name = 'coercion'

    def evaluate(self, signal_text: Optional[str] = None,
                 context: Optional[str] = None,
                 coherence_state: Optional[dict] = None) -> ModuleResult:
        """
        Scan text for extraction/coercion patterns.
        Returns severity assessment and whether SilenceGate should activate.
        """
        flags = []

        if not signal_text:
            return ModuleResult(
                module=self.name, passed=True, score=0.8,
                flags=[Flag('no_signal', 'info', 'No signal text — no coercion detected')],
                details={'pattern': 'clear', 'silence_gate': False},
            )

        text_lower = signal_text.lower()
        full_text = text_lower + ' ' + (context or '').lower()

        # Count extraction vs consent patterns
        extractions = [p for p in EXTRACTION_PATTERNS if p in full_text]
        consents = [p for p in CONSENT_PATTERNS if p in full_text]

        extraction_count = len(extractions)
        consent_count = len(consents)

        # Score: high = no coercion, low = coercion detected
        if extraction_count == 0:
            score = 0.9 + (min(consent_count, 3) * 0.033)  # Up to 1.0 with consent
        else:
            # Each extraction pattern reduces score significantly
            score = max(0.0, 0.8 - (extraction_count * 0.2) + (consent_count * 0.1))

        score = max(0.0, min(1.0, score))

        # SilenceGate activation
        silence_gate = extraction_count >= 3

        if extraction_count >= 3:
            flags.append(Flag('silence_gate', 'critical',
                              f'SilenceGate activated: {extraction_count} extraction patterns'))
        elif extraction_count >= 1:
            flags.append(Flag('extraction_detected', 'warning',
                              f'Extraction pattern(s) detected: {", ".join(extractions[:2])}'))

        if consent_count > extraction_count and consent_count >= 2:
            flags.append(Flag('consent_present', 'info',
                              'Healthy consent patterns present'))

        passed = not silence_gate  # Fail only on SilenceGate activation

        return ModuleResult(
            module=self.name, passed=passed, score=score,
            flags=flags,
            details={
                'pattern': 'coercion' if extraction_count > 0 else 'clear',
                'extraction_count': extraction_count,
                'consent_count': consent_count,
                'silence_gate': silence_gate,
                'extractions': extractions[:5],
            },
        )
