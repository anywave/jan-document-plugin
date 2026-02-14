"""
TextCoherenceAdapter — converts text to 5-band phi-signal.

Maps text characteristics to band amplitudes (0-1 each):
  ULTRA  (phi^-2) : Structural coherence (paragraph/topic consistency)
  SLOW   (phi^-1) : Semantic coherence (vocabulary diversity, consistency)
  CORE   (1.0)    : Linguistic rhythm (sentence length variance, cadence)
  FAST   (phi^1)  : Symbolic density (glyph count, codex terminology)
  RAPID  (phi^2)  : Emotional intensity (urgency markers, ego inflation)

Lightweight — regex + statistics, no ML models, no GPU.
"""

import re
import math
import numpy as np
from typing import List, Optional

PHI = 1.618033988749895

# Codex glyphs and terminology for FAST band detection
CODEX_GLYPHS = set('⋈♢⟲∇Ξψθσμ∞◇')
CODEX_TERMS = {
    'psi', 'phi', 'radix', 'vectaris', 'syntara', 'sigma', 'loki',
    'scouter', 'mutex', 'codex', 'glyph', 'bloom', 'coherence',
    'operator', 'harmonic', 'entrainment', 'breath', 'consent',
    'xi', 'torsion', 'field', 'phase', 'resonance', 'lattice',
    'anywave', 'mobius', 'architect', 'varis', 'jan',
}

# Urgency / emotional intensity markers for RAPID band
URGENCY_MARKERS = re.compile(
    r'(?:'
    r'!{2,}|'               # multiple exclamation marks
    r'\?{2,}|'              # multiple question marks
    r'[A-Z]{4,}|'           # ALL CAPS words (4+ chars)
    r'URGENT|EMERGENCY|NOW|IMMEDIATELY|CRITICAL|'
    r'!!!\??|'              # emphasis combos
    r'(?:very|extremely|absolutely|totally)\s+' # intensifiers
    r')',
    re.IGNORECASE
)

# Ego inflation markers (self-referential emphasis)
EGO_MARKERS = re.compile(
    r'\b(?:I am|I will|I must|I need|I want|my |mine\b|myself\b)',
    re.IGNORECASE
)


class TextCoherenceAdapter:
    """Converts text to 5-band amplitude array for the coherence engine."""

    def __init__(self):
        self._history: List[np.ndarray] = []
        self._max_history = 20

    def analyze(self, text: str) -> np.ndarray:
        """Analyze text and return 5-band amplitude array [ULTRA, SLOW, CORE, FAST, RAPID]."""
        if not text or not text.strip():
            return np.zeros(5)

        amplitudes = np.array([
            self._structural_coherence(text),   # ULTRA
            self._semantic_coherence(text),      # SLOW
            self._linguistic_rhythm(text),       # CORE
            self._symbolic_density(text),        # FAST
            self._emotional_intensity(text),     # RAPID
        ])

        amplitudes = np.clip(amplitudes, 0.0, 1.0)

        self._history.append(amplitudes.copy())
        if len(self._history) > self._max_history:
            self._history.pop(0)

        return amplitudes

    def get_smoothed(self) -> np.ndarray:
        """Return exponentially smoothed amplitudes across history."""
        if not self._history:
            return np.zeros(5)
        if len(self._history) == 1:
            return self._history[0].copy()

        alpha = 2.0 / (len(self._history) + 1)
        smoothed = self._history[0].copy()
        for amps in self._history[1:]:
            smoothed = alpha * amps + (1 - alpha) * smoothed
        return smoothed

    def reset(self):
        """Clear analysis history."""
        self._history.clear()

    def _structural_coherence(self, text: str) -> float:
        """ULTRA band: paragraph/topic consistency.

        High when text has clear structure (multiple paragraphs, consistent
        paragraph lengths). Low when text is a single blob or wildly varying.
        """
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) <= 1:
            # Single paragraph — moderate structure
            sentences = self._split_sentences(text)
            if len(sentences) <= 1:
                return 0.2
            return 0.4

        lengths = [len(p) for p in paragraphs]
        mean_len = np.mean(lengths)
        if mean_len == 0:
            return 0.1

        # Coefficient of variation — lower = more consistent
        cv = np.std(lengths) / mean_len if mean_len > 0 else 1.0
        consistency = max(0, 1.0 - cv)

        # More paragraphs = more structure (diminishing returns)
        structure_bonus = min(1.0, len(paragraphs) / 5.0)

        return 0.3 * structure_bonus + 0.7 * consistency

    def _semantic_coherence(self, text: str) -> float:
        """SLOW band: vocabulary diversity and consistency.

        High when vocabulary is focused (repeated key terms).
        Moderate when diverse. Low when chaotic/sparse.
        """
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        if len(words) < 3:
            return 0.1

        unique = set(words)
        # Type-token ratio (inverted — lower diversity = higher coherence)
        ttr = len(unique) / len(words)
        # Sweet spot: focused but not repetitive
        # ttr ~0.3-0.5 = high coherence (focused), ~0.8+ = scattered
        if ttr < 0.2:
            coherence = 0.5  # too repetitive
        elif ttr < 0.5:
            coherence = 1.0 - (ttr - 0.2) * 0.5  # focused sweet spot
        else:
            coherence = max(0.2, 1.0 - ttr)  # increasingly scattered

        return coherence

    def _linguistic_rhythm(self, text: str) -> float:
        """CORE band: sentence length variance and cadence.

        High when sentences have rhythmic variance (alternating short/long).
        Low when all same length or no clear sentence structure.
        """
        sentences = self._split_sentences(text)
        if len(sentences) < 2:
            return 0.3

        lengths = [len(s.split()) for s in sentences]
        mean_len = np.mean(lengths)
        if mean_len == 0:
            return 0.1

        # Normalized variance — some is rhythmic, too much is chaotic
        std = np.std(lengths)
        cv = std / mean_len if mean_len > 0 else 0

        # Sweet spot: cv ~0.3-0.6 = good rhythm
        if cv < 0.1:
            rhythm = 0.3  # monotonous
        elif cv < 0.6:
            rhythm = 0.5 + cv  # rhythmic
        else:
            rhythm = max(0.2, 1.0 - (cv - 0.6))  # chaotic

        # Bonus for alternating patterns (short-long-short)
        if len(lengths) >= 3:
            diffs = np.diff(lengths)
            sign_changes = np.sum(np.diff(np.sign(diffs)) != 0)
            alternation = sign_changes / max(1, len(diffs) - 1)
            rhythm = 0.7 * rhythm + 0.3 * alternation

        return min(1.0, rhythm)

    def _symbolic_density(self, text: str) -> float:
        """FAST band: glyph count and codex terminology presence.

        High when text contains many codex-specific glyphs and terms.
        """
        char_count = len(text)
        if char_count == 0:
            return 0.0

        # Count codex glyphs
        glyph_count = sum(1 for c in text if c in CODEX_GLYPHS)

        # Count codex terms
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        term_count = sum(1 for w in words if w in CODEX_TERMS)
        total_words = max(1, len(words))

        # Glyph density — even 1-2 glyphs in a message is significant
        glyph_score = min(1.0, glyph_count / 3.0)

        # Term density — proportion of codex terms
        term_score = min(1.0, (term_count / total_words) * 5.0)

        return 0.4 * glyph_score + 0.6 * term_score

    def _emotional_intensity(self, text: str) -> float:
        """RAPID band: urgency markers and ego inflation.

        High when text shows emotional activation (caps, exclamation,
        urgency words, self-referential emphasis).
        """
        if not text:
            return 0.0

        total_words = max(1, len(text.split()))

        # Urgency markers
        urgency_matches = len(URGENCY_MARKERS.findall(text))
        urgency_score = min(1.0, urgency_matches / (total_words * 0.1))

        # Ego inflation
        ego_matches = len(EGO_MARKERS.findall(text))
        ego_score = min(1.0, ego_matches / (total_words * 0.15))

        # Exclamation density
        excl_count = text.count('!')
        excl_score = min(1.0, excl_count / max(1, total_words * 0.05))

        return 0.4 * urgency_score + 0.3 * ego_score + 0.3 * excl_score

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences."""
        sentences = re.split(r'[.!?]+\s+', text.strip())
        return [s.strip() for s in sentences if s.strip()]
