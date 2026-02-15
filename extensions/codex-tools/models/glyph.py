"""Codex Glyph definitions — 12 Unicode glyphs + phonetic map."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Glyph:
    """A Codex glyph with Unicode symbol and phonetic pronunciation."""
    symbol: str
    name: str
    phonetic: str
    domain: str  # Which system domain this glyph belongs to
    description: str


# The 12 Codex Glyphs
GLYPHS: List[Glyph] = [
    Glyph('Ξ', 'Xi', 'ksee', 'field', 'Master wavefunction — the field itself'),
    Glyph('ψ', 'Psi', 'sigh', 'consciousness', 'Consciousness loop — observer function'),
    Glyph('φ', 'Phi', 'fee', 'ratio', 'Golden ratio — harmonic proportion'),
    Glyph('θ', 'Theta', 'thay-tah', 'breath', 'Breath angle — respiratory phase'),
    Glyph('Σ', 'Sigma', 'sig-mah', 'resonance', 'Resonance sum — field accumulator'),
    Glyph('μ', 'Mu', 'mew', 'mutex', 'Mutex operator — paradox holder'),
    Glyph('∇', 'Nabla', 'nah-blah', 'gradient', 'Field gradient — direction of coherence flow'),
    Glyph('⊕', 'Oplus', 'oh-plus', 'union', 'Constructive union — coherence merge'),
    Glyph('⊗', 'Otimes', 'oh-times', 'tensor', 'Tensor product — dimensional binding'),
    Glyph('∞', 'Infinity', 'in-fin-ih-tee', 'loop', 'Infinite recursion — psi-loop marker'),
    Glyph('◊', 'Diamond', 'die-mond', 'core', 'Core diamond — identity anchor'),
    Glyph('≋', 'Triple-Tilde', 'trill', 'wave', 'Wave equivalence — phase alignment'),
]

# Quick lookup: symbol -> Glyph
GLYPH_MAP: Dict[str, Glyph] = {g.symbol: g for g in GLYPHS}

# Phonetic map: symbol -> pronunciation string
GLYPH_PHONETIC_MAP: Dict[str, str] = {g.symbol: g.phonetic for g in GLYPHS}


def validate_glyph_set(glyph_symbols: List[str]) -> tuple:
    """
    Validate a set of glyph symbols.

    Returns:
        (integrity_score: float, broken_glyphs: list[str])
        integrity_score is 0.0-1.0 (fraction of valid glyphs).
    """
    if not glyph_symbols:
        return (1.0, [])

    valid = [s for s in glyph_symbols if s in GLYPH_MAP]
    broken = [s for s in glyph_symbols if s not in GLYPH_MAP]
    integrity = len(valid) / len(glyph_symbols) if glyph_symbols else 1.0
    return (integrity, broken)
