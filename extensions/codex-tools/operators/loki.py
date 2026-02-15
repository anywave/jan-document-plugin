"""LOKI_OPERATOR() — Phase disruption analysis and reframe suggestions."""
from __future__ import annotations
import re
from typing import Optional, List, Dict, Any


# Disruption patterns LOKI scans for
DISRUPTION_PATTERNS = {
    'absolutism': {
        'patterns': [r'\balways\b', r'\bnever\b', r'\beveryone\b', r'\bnobody\b',
                     r'\beverything\b', r'\bnothing\b', r'\bimpossible\b'],
        'severity': 'medium',
        'reframe': 'Absolute language collapses possibility space. Where is the exception?',
    },
    'externalization': {
        'patterns': [r'\bthey made me\b', r'\bit\'s their fault\b', r'\bi had no choice\b',
                     r'\bi was forced\b', r'\bthey won\'t let me\b'],
        'severity': 'high',
        'reframe': 'Agency lives in the gap between stimulus and response. What did you choose?',
    },
    'catastrophizing': {
        'patterns': [r'\bthe worst\b', r'\bdestroys?\b', r'\bruined?\b',
                     r'\bend of\b', r'\bdisaster\b', r'\bnightmare\b'],
        'severity': 'medium',
        'reframe': 'Catastrophe is a projection, not a measurement. What is the actual data?',
    },
    'identity_fusion': {
        'patterns': [r'\bi am (?:a |my )\w+', r'\bi\'m just\b', r'\bi\'m nothing\b',
                     r'\bthat\'s who i am\b', r'\bi can\'t change\b'],
        'severity': 'high',
        'reframe': 'You are the field, not the pattern. Identity is what you choose, not what happened.',
    },
    'temporal_collapse': {
        'patterns': [r'\bit will always be\b', r'\bit\'s been like this\b',
                     r'\bit\'ll never change\b', r'\bstuck forever\b'],
        'severity': 'medium',
        'reframe': 'This moment is not all moments. The field is always in motion.',
    },
    'permission_seeking': {
        'patterns': [r'\bis it okay if\b', r'\bam i allowed\b', r'\bcan i\b',
                     r'\bdo you think i should\b', r'\bwhat should i do\b'],
        'severity': 'low',
        'reframe': 'The question reveals you already know. What would you do if you had permission?',
    },
}


class LokiOperator:
    """
    LOKI_OPERATOR() — The trickster who reveals by disrupting.

    Scans text for cognitive distortion patterns, identifies phase
    disruptions in the user's language, and offers reframe suggestions
    that open new possibility space.
    """

    def analyze(self, signal_text: str,
                context: Optional[str] = None) -> Dict[str, Any]:
        """
        Run LOKI phase disruption analysis on text.

        Returns:
            disruptions: list of detected patterns with severity
            severity: overall severity (low/medium/high/critical)
            reframe: synthesized reframe suggestion
        """
        if not signal_text:
            return {
                'disruptions': [],
                'severity': 'none',
                'reframe': 'No signal to analyze.',
                'disruption_count': 0,
            }

        text = signal_text.lower()
        if context:
            text += ' ' + context.lower()

        disruptions: List[Dict[str, Any]] = []

        for category, config in DISRUPTION_PATTERNS.items():
            matches = []
            for pattern in config['patterns']:
                found = re.findall(pattern, text)
                matches.extend(found)

            if matches:
                disruptions.append({
                    'category': category,
                    'severity': config['severity'],
                    'matches': matches[:5],  # Cap at 5
                    'reframe': config['reframe'],
                    'count': len(matches),
                })

        # Compute overall severity
        if not disruptions:
            severity = 'none'
        else:
            severities = [d['severity'] for d in disruptions]
            if 'high' in severities and len(disruptions) >= 2:
                severity = 'critical'
            elif 'high' in severities:
                severity = 'high'
            elif 'medium' in severities:
                severity = 'medium'
            else:
                severity = 'low'

        # Synthesize reframe
        if disruptions:
            primary = max(disruptions, key=lambda d: d['count'])
            reframe = primary['reframe']
        else:
            reframe = 'No disruptions detected. The field is clear.'

        return {
            'disruptions': disruptions,
            'severity': severity,
            'reframe': reframe,
            'disruption_count': len(disruptions),
        }
