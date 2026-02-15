"""Tests for QSE operators: LOKI, Glyph Engine, Tarot."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from operators.loki import LokiOperator
from operators.glyph_engine import GlyphSandbox
from operators.tarot import TarotOperatorRunner
from models.state import QSEState


class TestLokiOperator:
    def setup_method(self):
        self.loki = LokiOperator()

    def test_clean_text(self):
        result = self.loki.analyze('I appreciate this beautiful day and feel grateful for life.')
        assert result['severity'] == 'none'
        assert result['disruption_count'] == 0

    def test_absolutism_detection(self):
        result = self.loki.analyze('I always fail at everything. Nobody ever helps me.')
        assert result['disruption_count'] >= 1
        categories = [d['category'] for d in result['disruptions']]
        assert 'absolutism' in categories

    def test_externalization_detection(self):
        result = self.loki.analyze("They made me do it. It's their fault. I had no choice.")
        categories = [d['category'] for d in result['disruptions']]
        assert 'externalization' in categories

    def test_catastrophizing(self):
        result = self.loki.analyze('This is the worst disaster. Everything is ruined.')
        categories = [d['category'] for d in result['disruptions']]
        assert 'catastrophizing' in categories

    def test_empty_text(self):
        result = self.loki.analyze('')
        assert result['severity'] == 'none'

    def test_reframe_provided(self):
        result = self.loki.analyze('Nobody cares. Everything is impossible. I always lose.')
        assert len(result['reframe']) > 0

    def test_multiple_disruptions_elevates_severity(self):
        result = self.loki.analyze(
            "They made me do it. I always fail. It's the worst. I can't change who I am."
        )
        # Multiple high-severity patterns should produce 'critical' or 'high'
        assert result['severity'] in ('high', 'critical')


class TestGlyphSandbox:
    def setup_method(self):
        self.sandbox = GlyphSandbox()

    def test_valid_glyphs(self):
        result = self.sandbox.validate(['\u039e', '\u03c8', '\u03c6'])  # Ξ, ψ, φ
        assert result['integrity_score'] == 1.0
        assert len(result['broken_glyphs']) == 0
        assert result['valid_count'] == 3

    def test_mixed_glyphs(self):
        result = self.sandbox.validate(['\u039e', 'X', '\u03c8', '!'])
        assert result['integrity_score'] == 0.5  # 2/4 valid
        assert 'X' in result['broken_glyphs']
        assert '!' in result['broken_glyphs']

    def test_empty_set(self):
        result = self.sandbox.validate([])
        assert result['integrity_score'] == 1.0
        assert result['total'] == 0

    def test_all_twelve(self):
        all_glyphs = ['\u039e', '\u03c8', '\u03c6', '\u03b8', '\u03a3', '\u03bc',
                      '\u2207', '\u2295', '\u2297', '\u221e', '\u25ca', '\u224b']
        result = self.sandbox.validate(all_glyphs)
        assert result['integrity_score'] == 1.0
        assert result['valid_count'] == 12


class TestTarotOperator:
    def setup_method(self):
        self.tarot = TarotOperatorRunner()

    def test_valid_card(self):
        result = self.tarot.run(0)  # The Fool
        assert 'card' in result
        assert result['card']['name'] == 'The Fool'
        assert result['card']['codex_name'] == 'ZERO_POINT'

    def test_all_cards(self):
        for i in range(22):
            result = self.tarot.run(i)
            assert 'card' in result
            assert result['card']['id'] == i

    def test_invalid_card(self):
        result = self.tarot.run(99)
        assert 'error' in result

    def test_with_field_state(self):
        state = {'scalarCoherence': 0.85, 'active': True}
        qse = QSEState(field_phase='active')
        result = self.tarot.run(19, state, qse)  # The Sun (full coherence)
        assert result['assessment']['status'] == 'assessed'
        assert result['assessment']['alignment'] > 0.5

    def test_no_data_symbolic_only(self):
        result = self.tarot.run(7)  # The Chariot
        assert result['assessment']['status'] == 'no_data'
        assert 'symbolic only' in result['assessment']['message']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
