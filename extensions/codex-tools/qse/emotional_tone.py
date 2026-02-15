"""Module 2: Emotional Tone — θ_neutral check, craving/guilt/nostalgia flags."""
from __future__ import annotations
from typing import List, Optional, Dict
from models.state import ModuleResult, Flag


# Emotional categories that disrupt coherence
DISRUPTIVE_TOKENS = {
    'craving': {'craving', 'want', 'need', 'desire', 'hunger', 'crave', 'longing',
                'obsess', 'fixate', 'attached'},
    'guilt': {'guilt', 'shame', 'blame', 'regret', 'sorry', 'fault', 'remorse',
              'punishment', 'unworthy', 'ashamed'},
    'nostalgia': {'nostalgia', 'remember when', 'miss', 'used to', 'back then',
                  'those days', 'wish things were', 'the way it was'},
    'fear': {'fear', 'afraid', 'terrified', 'anxious', 'dread', 'panic',
             'worry', 'scared', 'frightened'},
    'anger': {'anger', 'rage', 'fury', 'hate', 'resent', 'bitter',
              'furious', 'hostile', 'vengeful'},
}

# Tokens that support coherence
COHERENT_TOKENS = {
    'presence': {'present', 'here', 'now', 'aware', 'notice', 'observe',
                 'witness', 'attention', 'mindful'},
    'acceptance': {'accept', 'allow', 'let', 'release', 'surrender',
                   'open', 'embrace', 'trust', 'faith'},
    'gratitude': {'grateful', 'thankful', 'appreciate', 'blessing',
                  'gift', 'grace', 'abundance'},
    'curiosity': {'curious', 'wonder', 'explore', 'discover', 'question',
                  'investigate', 'fascinating', 'interesting'},
}


class EmotionalToneModule:
    """Validates emotional field tone for coherence compatibility."""

    name = 'emotional_tone'

    def evaluate(self, emotional_tokens: Optional[List[str]] = None,
                 coherence_state: Optional[dict] = None) -> ModuleResult:
        """
        Analyze emotional tokens for coherence-disruptive patterns.
        θ_neutral = no dominant disruptive emotional pattern.
        """
        flags: List[Flag] = []

        if not emotional_tokens:
            # No explicit tokens — neutral pass
            return ModuleResult(
                module=self.name, passed=True, score=0.7,
                flags=[Flag('no_tokens', 'info', 'No emotional tokens provided — neutral')],
                details={'tone_class': 'neutral'},
            )

        tokens_lower = [t.lower().strip() for t in emotional_tokens]
        token_set = set(tokens_lower)

        # Count disruptive and coherent matches
        disruptions: Dict[str, List[str]] = {}
        coherent: Dict[str, List[str]] = {}

        for category, keywords in DISRUPTIVE_TOKENS.items():
            matches = [t for t in tokens_lower if t in keywords]
            if matches:
                disruptions[category] = matches

        for category, keywords in COHERENT_TOKENS.items():
            matches = [t for t in tokens_lower if t in keywords]
            if matches:
                coherent[category] = matches

        total = len(emotional_tokens)
        disruptive_count = sum(len(v) for v in disruptions.values())
        coherent_count = sum(len(v) for v in coherent.values())

        # Score: coherent tokens boost, disruptive tokens reduce
        base_score = 0.5  # neutral baseline
        if total > 0:
            coherent_ratio = coherent_count / total
            disruptive_ratio = disruptive_count / total
            base_score = 0.5 + (coherent_ratio * 0.5) - (disruptive_ratio * 0.5)
        score = max(0.0, min(1.0, base_score))

        # Flag disruptive patterns
        for category, matches in disruptions.items():
            severity = 'critical' if len(matches) >= 3 else 'warning'
            flags.append(Flag(
                f'disruptive_{category}', severity,
                f'{category.title()} pattern detected: {", ".join(matches[:3])}'
            ))

        # Determine tone class
        if disruptive_count > coherent_count and disruptive_count >= 2:
            tone_class = 'disruptive'
        elif coherent_count > disruptive_count and coherent_count >= 2:
            tone_class = 'coherent'
        else:
            tone_class = 'neutral'

        passed = score >= 0.4  # Low bar — only fail on strong disruption

        return ModuleResult(
            module=self.name, passed=passed, score=score,
            flags=flags,
            details={
                'tone_class': tone_class,
                'disruptive_categories': list(disruptions.keys()),
                'coherent_categories': list(coherent.keys()),
                'disruptive_count': disruptive_count,
                'coherent_count': coherent_count,
                'total_tokens': total,
            },
        )
