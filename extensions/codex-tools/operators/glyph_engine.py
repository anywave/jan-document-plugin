"""GLYPH_SANDBOX() — Glyph integrity validation."""
from __future__ import annotations
from typing import List, Dict, Any
from models.glyph import GLYPH_MAP, validate_glyph_set, GLYPHS


class GlyphSandbox:
    """
    GLYPH_SANDBOX() — Validates glyph set integrity.

    Checks that glyphs are recognized Codex symbols, reports
    integrity score, and identifies any broken/unknown glyphs.
    """

    def validate(self, glyph_symbols: List[str]) -> Dict[str, Any]:
        """
        Validate a set of glyph symbols against the Codex glyph catalog.

        Returns:
            integrity_score: 0.0-1.0 (fraction valid)
            broken_glyphs: list of unrecognized symbols
            valid_glyphs: list of recognized glyphs with metadata
        """
        integrity, broken = validate_glyph_set(glyph_symbols)

        valid_info = []
        for symbol in glyph_symbols:
            if symbol in GLYPH_MAP:
                g = GLYPH_MAP[symbol]
                valid_info.append({
                    'symbol': g.symbol,
                    'name': g.name,
                    'phonetic': g.phonetic,
                    'domain': g.domain,
                })

        return {
            'integrity_score': integrity,
            'broken_glyphs': broken,
            'valid_glyphs': valid_info,
            'total': len(glyph_symbols),
            'valid_count': len(glyph_symbols) - len(broken),
            'catalog_size': len(GLYPHS),
        }
