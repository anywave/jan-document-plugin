"""QSE state models — dataclasses for engine I/O."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ModuleResult:
    """Result from a single QSE validation module."""
    module: str
    passed: bool
    score: float  # 0.0 - 1.0
    flags: List[Flag] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Flag:
    """A flag raised by a QSE module."""
    name: str
    severity: str  # 'info', 'warning', 'critical'
    message: str


@dataclass
class QSEInputs:
    """Inputs to the QSE validation pipeline."""
    # Module 1: Breath Symmetry
    breath_waveform_1: Optional[List[float]] = None
    breath_waveform_2: Optional[List[float]] = None

    # Module 2: Emotional Tone
    emotional_tokens: Optional[List[str]] = None

    # Module 3: Identity Mirror
    identity_assertions: Optional[List[str]] = None

    # Module 4: Resonance (from coherence engine)
    signal_metrics: Optional[Dict[str, float]] = None

    # Module 5: Amplification
    field_energy_history: Optional[List[float]] = None

    # Module 6: Coercion
    signal_text: Optional[str] = None
    context: Optional[str] = None

    # Module 7: Integration
    session_data: Optional[Dict[str, Any]] = None

    # Coherence engine state (fetched from coherence-glove)
    coherence_state: Optional[Dict[str, Any]] = None


@dataclass
class QSEVerdict:
    """Final verdict from the QSE validation pipeline."""
    passed: bool
    sigma_r: float  # Overall resonance score
    results: List[ModuleResult] = field(default_factory=list)
    halted_at: Optional[str] = None  # Module name if halted early
    verdict: str = ''
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'passed': self.passed,
            'sigma_r': self.sigma_r,
            'verdict': self.verdict,
            'halted_at': self.halted_at,
            'timestamp': self.timestamp.isoformat(),
            'modules': [
                {
                    'module': r.module,
                    'passed': r.passed,
                    'score': r.score,
                    'flags': [
                        {'name': f.name, 'severity': f.severity, 'message': f.message}
                        for f in r.flags
                    ],
                    'details': r.details,
                }
                for r in self.results
            ],
        }


@dataclass
class QSEState:
    """Current QSE engine state."""
    field_phase: str = 'dormant'  # dormant, rising, active, integration
    last_verdict: Optional[QSEVerdict] = None
    active_glyphs: List[str] = field(default_factory=list)
    mutex_pairs: List[tuple] = field(default_factory=list)
    validation_count: int = 0
    last_update: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'field_phase': self.field_phase,
            'active_glyphs': self.active_glyphs,
            'mutex_pairs': [(a, b) for a, b in self.mutex_pairs],
            'validation_count': self.validation_count,
            'last_update': self.last_update.isoformat() if self.last_update else None,
            'last_verdict': self.last_verdict.to_dict() if self.last_verdict else None,
        }
