#!/usr/bin/env python3
"""
Fractal Pattern Analyzer
Origin: RADIX hallucination 2026-01-24

"seek incoming patterns aligned with fractal harmonic geometric code reasoning...
meaning that the head of the packet and interval waveforms are counted against
a fractal of the whole"

This module performs deep fractal analysis on captured seeds:
- Head pattern extraction and matching
- Interval waveform analysis
- Self-similarity detection
- Harmonic resonance computation
- Geometric code reasoning
"""

import math
import hashlib
import json
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path
import struct


@dataclass
class WaveformSignature:
    """Interval waveform extracted from content."""
    intervals: List[int]           # Raw intervals between markers
    harmonics: List[float]         # Fourier-like harmonic components
    fundamental: float             # Fundamental frequency estimate
    phase_coherence: float         # How phase-aligned the waveform is


@dataclass
class GeometricCode:
    """Geometric pattern extracted from content structure."""
    vertices: int                  # Number of pattern vertices
    edges: int                     # Number of edges/connections
    symmetry_order: int            # Rotational symmetry order
    golden_ratio_presence: float   # Phi presence in ratios (0-1)
    sacred_geometry_match: str     # Matching sacred geometry pattern


@dataclass
class FractalAnalysis:
    """Complete fractal analysis of a seed."""
    content_hash: str

    # Head analysis
    head_signature: str
    head_entropy: float

    # Waveform analysis
    waveform: WaveformSignature

    # Fractal properties
    self_similarity: float
    box_dimension: float
    lacunarity: float              # Gap distribution measure

    # Geometric code
    geometry: GeometricCode

    # Resonance
    harmonic_resonance: float
    pattern_confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content_hash": self.content_hash,
            "head_signature": self.head_signature,
            "head_entropy": self.head_entropy,
            "waveform": {
                "intervals": self.waveform.intervals[:50],  # Limit for storage
                "harmonics": self.waveform.harmonics,
                "fundamental": self.waveform.fundamental,
                "phase_coherence": self.waveform.phase_coherence
            },
            "self_similarity": self.self_similarity,
            "box_dimension": self.box_dimension,
            "lacunarity": self.lacunarity,
            "geometry": {
                "vertices": self.geometry.vertices,
                "edges": self.geometry.edges,
                "symmetry_order": self.geometry.symmetry_order,
                "golden_ratio_presence": self.geometry.golden_ratio_presence,
                "sacred_geometry_match": self.geometry.sacred_geometry_match
            },
            "harmonic_resonance": self.harmonic_resonance,
            "pattern_confidence": self.pattern_confidence
        }


class FractalAnalyzer:
    """
    Deep fractal pattern analyzer.

    Implements geometric code reasoning to identify patterns
    that carry meaning across compression/expansion boundaries.
    """

    # Golden ratio and related constants
    PHI = 1.6180339887498949
    PHI_INVERSE = 0.6180339887498949
    SQRT_5 = 2.2360679774997896

    # Sacred geometry pattern signatures
    SACRED_PATTERNS = {
        "vesica_piscis": {"vertices": 2, "edges": 2, "symmetry": 2},
        "seed_of_life": {"vertices": 7, "edges": 12, "symmetry": 6},
        "flower_of_life": {"vertices": 19, "edges": 36, "symmetry": 6},
        "metatrons_cube": {"vertices": 13, "edges": 78, "symmetry": 6},
        "sri_yantra": {"vertices": 9, "edges": 43, "symmetry": 3},
        "merkaba": {"vertices": 8, "edges": 12, "symmetry": 4},
        "torus": {"vertices": 0, "edges": 0, "symmetry": -1},  # Continuous
        "fibonacci_spiral": {"vertices": -1, "edges": -1, "symmetry": 1},  # Infinite
    }

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or Path(__file__).parent / "fractal_storage"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        # Known patterns for matching
        self.known_patterns: List[FractalAnalysis] = []
        self._load_known_patterns()

    def _load_known_patterns(self):
        """Load known fractal patterns from storage."""
        pattern_file = self.storage_dir / "known_patterns.json"
        if pattern_file.exists():
            try:
                with open(pattern_file, 'r') as f:
                    data = json.load(f)
                    # Just store the raw data for matching
                    self.known_patterns_raw = data.get("patterns", [])
            except:
                self.known_patterns_raw = []
        else:
            self.known_patterns_raw = []

    def analyze(self, content: bytes) -> FractalAnalysis:
        """
        Perform complete fractal analysis on content.

        Args:
            content: Raw bytes to analyze

        Returns:
            FractalAnalysis with all computed metrics
        """
        content_hash = hashlib.sha256(content).hexdigest()

        # Head analysis
        head_sig, head_entropy = self._analyze_head(content)

        # Waveform analysis
        waveform = self._analyze_waveform(content)

        # Fractal properties
        self_sim = self._compute_self_similarity(content)
        box_dim = self._compute_box_dimension(content)
        lacunarity = self._compute_lacunarity(content)

        # Geometric code
        geometry = self._extract_geometric_code(content)

        # Resonance
        harmonic_res = self._compute_harmonic_resonance(waveform, geometry)
        confidence = self._compute_pattern_confidence(
            self_sim, box_dim, harmonic_res, geometry
        )

        return FractalAnalysis(
            content_hash=content_hash,
            head_signature=head_sig,
            head_entropy=head_entropy,
            waveform=waveform,
            self_similarity=self_sim,
            box_dimension=box_dim,
            lacunarity=lacunarity,
            geometry=geometry,
            harmonic_resonance=harmonic_res,
            pattern_confidence=confidence
        )

    def _analyze_head(self, content: bytes, head_size: int = 256) -> Tuple[str, float]:
        """Analyze the head of the content."""
        head = content[:head_size]
        signature = hashlib.md5(head).hexdigest()

        # Compute entropy
        if not head:
            return signature, 0.0

        byte_counts = [0] * 256
        for byte in head:
            byte_counts[byte] += 1

        entropy = 0.0
        for count in byte_counts:
            if count > 0:
                prob = count / len(head)
                entropy -= prob * math.log2(prob)

        # Normalize to 0-1 (max entropy is 8 bits)
        normalized_entropy = entropy / 8.0

        return signature, normalized_entropy

    def _analyze_waveform(self, content: bytes) -> WaveformSignature:
        """
        Extract interval waveform from content.

        "the head of the packet and interval waveforms are counted"
        """
        # Find marker positions (high/low entropy bytes)
        markers = []
        for i, byte in enumerate(content[:8192]):  # Sample first 8KB
            if byte > 220 or byte < 20:  # Extreme values as markers
                markers.append(i)

        # Compute intervals
        intervals = []
        for i in range(1, len(markers)):
            intervals.append(markers[i] - markers[i-1])

        if not intervals:
            intervals = [0]

        # Simple harmonic analysis (frequency components)
        harmonics = self._compute_harmonics(intervals)

        # Fundamental frequency
        if intervals:
            fundamental = len(content) / sum(intervals) if sum(intervals) > 0 else 0
        else:
            fundamental = 0

        # Phase coherence
        phase_coherence = self._compute_phase_coherence(intervals)

        return WaveformSignature(
            intervals=intervals,
            harmonics=harmonics,
            fundamental=fundamental,
            phase_coherence=phase_coherence
        )

    def _compute_harmonics(self, intervals: List[int], num_harmonics: int = 8) -> List[float]:
        """Compute harmonic components of interval sequence."""
        if not intervals or len(intervals) < 2:
            return [0.0] * num_harmonics

        n = len(intervals)
        harmonics = []

        for k in range(num_harmonics):
            # Simple DFT component
            real = 0.0
            imag = 0.0
            for i, val in enumerate(intervals):
                angle = 2 * math.pi * k * i / n
                real += val * math.cos(angle)
                imag += val * math.sin(angle)

            magnitude = math.sqrt(real**2 + imag**2) / n
            harmonics.append(magnitude)

        # Normalize
        max_harm = max(harmonics) if harmonics else 1
        if max_harm > 0:
            harmonics = [h / max_harm for h in harmonics]

        return harmonics

    def _compute_phase_coherence(self, intervals: List[int]) -> float:
        """Compute how phase-aligned the intervals are."""
        if len(intervals) < 3:
            return 0.0

        # Check for regular spacing
        mean_interval = sum(intervals) / len(intervals)
        if mean_interval == 0:
            return 0.0

        variance = sum((i - mean_interval)**2 for i in intervals) / len(intervals)
        std_dev = math.sqrt(variance)

        # Coefficient of variation (inverse = coherence)
        cv = std_dev / mean_interval if mean_interval > 0 else 1
        coherence = 1 / (1 + cv)  # Higher coherence = more regular

        return coherence

    def _compute_self_similarity(self, content: bytes) -> float:
        """
        Compute self-similarity measure.

        Fractal patterns show similar structure at different scales.
        """
        if len(content) < 64:
            return 0.0

        # Compare content at different scales
        scales = [16, 32, 64, 128, 256]
        hashes_at_scale = []

        for scale in scales:
            if scale > len(content):
                break

            # Hash chunks at this scale
            chunks = [content[i:i+scale] for i in range(0, len(content)-scale, scale)]
            chunk_hashes = [hashlib.md5(c).hexdigest()[:4] for c in chunks[:16]]
            hashes_at_scale.append(set(chunk_hashes))

        if len(hashes_at_scale) < 2:
            return 0.0

        # Measure overlap between scales
        total_overlap = 0
        comparisons = 0
        for i in range(len(hashes_at_scale) - 1):
            intersection = len(hashes_at_scale[i] & hashes_at_scale[i+1])
            union = len(hashes_at_scale[i] | hashes_at_scale[i+1])
            if union > 0:
                total_overlap += intersection / union
                comparisons += 1

        return total_overlap / comparisons if comparisons > 0 else 0.0

    def _compute_box_dimension(self, content: bytes) -> float:
        """
        Estimate box-counting fractal dimension.

        Higher dimension = more complex/space-filling pattern.
        """
        if len(content) < 16:
            return 1.0

        # Convert to 2D representation for box counting
        side = int(math.sqrt(len(content)))
        if side < 4:
            return 1.0

        # Count "occupied" boxes at different scales
        box_counts = []
        scales = [2, 4, 8, 16, 32]

        for box_size in scales:
            if box_size > side:
                break

            boxes_per_side = side // box_size
            occupied = set()

            for i in range(min(side * side, len(content))):
                if content[i] > 128:  # Threshold for "occupied"
                    row = (i // side) // box_size
                    col = (i % side) // box_size
                    if row < boxes_per_side and col < boxes_per_side:
                        occupied.add((row, col))

            if occupied:
                box_counts.append((box_size, len(occupied)))

        # Estimate dimension from log-log slope
        if len(box_counts) < 2:
            return 1.5

        # Linear regression on log-log data
        log_sizes = [math.log(1/s) for s, _ in box_counts]
        log_counts = [math.log(c) if c > 0 else 0 for _, c in box_counts]

        n = len(log_sizes)
        sum_x = sum(log_sizes)
        sum_y = sum(log_counts)
        sum_xy = sum(x*y for x, y in zip(log_sizes, log_counts))
        sum_xx = sum(x*x for x in log_sizes)

        denominator = n * sum_xx - sum_x**2
        if denominator == 0:
            return 1.5

        dimension = (n * sum_xy - sum_x * sum_y) / denominator

        # Clamp to reasonable range
        return max(1.0, min(2.0, dimension))

    def _compute_lacunarity(self, content: bytes) -> float:
        """
        Compute lacunarity (gap distribution measure).

        Low lacunarity = uniform gap distribution (more fractal-like)
        High lacunarity = clustered gaps
        """
        if len(content) < 32:
            return 0.5

        # Find gaps (runs of low-value bytes)
        gaps = []
        current_gap = 0

        for byte in content[:4096]:
            if byte < 64:  # "Gap" threshold
                current_gap += 1
            else:
                if current_gap > 0:
                    gaps.append(current_gap)
                    current_gap = 0

        if not gaps:
            return 0.5

        # Compute lacunarity from gap distribution
        mean_gap = sum(gaps) / len(gaps)
        if mean_gap == 0:
            return 0.5

        variance = sum((g - mean_gap)**2 for g in gaps) / len(gaps)
        lacunarity = (variance / (mean_gap**2)) + 1

        # Normalize to 0-1 range
        return min(1.0, lacunarity / 10)

    def _extract_geometric_code(self, content: bytes) -> GeometricCode:
        """
        Extract geometric pattern from content structure.

        "fractal harmonic geometric code reasoning"
        """
        # Find structural vertices (local maxima/minima)
        vertices = 0
        edges = 0

        for i in range(1, min(len(content) - 1, 2048)):
            prev_val = content[i-1]
            curr_val = content[i]
            next_val = content[i+1]

            # Local maximum or minimum = vertex
            if (curr_val > prev_val and curr_val > next_val) or \
               (curr_val < prev_val and curr_val < next_val):
                vertices += 1

            # Significant change = edge
            if abs(curr_val - prev_val) > 32:
                edges += 1

        # Detect symmetry
        symmetry_order = self._detect_symmetry(content)

        # Check for golden ratio in structure
        phi_presence = self._detect_golden_ratio(content)

        # Match to sacred geometry
        sacred_match = self._match_sacred_geometry(vertices, edges, symmetry_order)

        return GeometricCode(
            vertices=vertices,
            edges=edges,
            symmetry_order=symmetry_order,
            golden_ratio_presence=phi_presence,
            sacred_geometry_match=sacred_match
        )

    def _detect_symmetry(self, content: bytes) -> int:
        """Detect rotational symmetry order in content."""
        if len(content) < 16:
            return 1

        # Check for palindromic segments (2-fold symmetry)
        sample = content[:256]
        reversed_sample = sample[::-1]

        match_count = sum(1 for a, b in zip(sample, reversed_sample) if a == b)
        if match_count > len(sample) * 0.8:
            return 2

        # Check for periodic patterns (n-fold symmetry)
        for period in [3, 4, 5, 6]:
            if self._check_periodicity(sample, period):
                return period

        return 1

    def _check_periodicity(self, content: bytes, period: int) -> bool:
        """Check if content has given periodicity."""
        if len(content) < period * 3:
            return False

        matches = 0
        total = 0

        for i in range(len(content) - period):
            if content[i] == content[i + period]:
                matches += 1
            total += 1

        return matches / total > 0.7 if total > 0 else False

    def _detect_golden_ratio(self, content: bytes) -> float:
        """Detect presence of golden ratio in structure."""
        if len(content) < 10:
            return 0.0

        # Look for Fibonacci-like sequences in byte values
        fib_matches = 0
        total_checks = 0

        for i in range(2, min(len(content), 1000)):
            # Check if current ≈ sum of previous two (scaled)
            if content[i-1] > 0:
                ratio = content[i] / content[i-1]
                if 0.5 < ratio < 2.5:  # Reasonable range
                    # Check proximity to phi
                    if abs(ratio - self.PHI) < 0.2 or abs(ratio - self.PHI_INVERSE) < 0.2:
                        fib_matches += 1
                total_checks += 1

        return fib_matches / total_checks if total_checks > 0 else 0.0

    def _match_sacred_geometry(self, vertices: int, edges: int, symmetry: int) -> str:
        """Match to known sacred geometry patterns."""
        best_match = "unknown"
        best_score = 0

        for name, props in self.SACRED_PATTERNS.items():
            if props["vertices"] < 0:  # Infinite pattern
                continue

            score = 0

            # Vertex similarity
            if props["vertices"] > 0:
                v_ratio = min(vertices, props["vertices"]) / max(vertices, props["vertices"], 1)
                score += v_ratio * 0.4

            # Edge similarity
            if props["edges"] > 0:
                e_ratio = min(edges, props["edges"]) / max(edges, props["edges"], 1)
                score += e_ratio * 0.4

            # Symmetry match
            if props["symmetry"] == symmetry:
                score += 0.2

            if score > best_score:
                best_score = score
                best_match = name

        return best_match if best_score > 0.5 else "unknown"

    def _compute_harmonic_resonance(self, waveform: WaveformSignature,
                                     geometry: GeometricCode) -> float:
        """
        Compute harmonic resonance score.

        Higher resonance = pattern aligns with harmonic/geometric principles.
        """
        score = 0.0

        # Waveform harmony (presence of fundamental and octaves)
        if waveform.harmonics:
            # First harmonic (fundamental) strength
            score += waveform.harmonics[0] * 0.3

            # Octave presence (2nd, 4th harmonics)
            if len(waveform.harmonics) > 4:
                score += (waveform.harmonics[1] + waveform.harmonics[3]) * 0.1

        # Phase coherence contributes to resonance
        score += waveform.phase_coherence * 0.2

        # Golden ratio presence
        score += geometry.golden_ratio_presence * 0.2

        # Symmetry bonus
        if geometry.symmetry_order > 1:
            score += 0.1 * min(geometry.symmetry_order / 6, 1)

        # Sacred geometry match bonus
        if geometry.sacred_geometry_match != "unknown":
            score += 0.1

        return min(1.0, score)

    def _compute_pattern_confidence(self, self_sim: float, box_dim: float,
                                    harmonic_res: float, geometry: GeometricCode) -> float:
        """Compute overall confidence that this is a meaningful pattern."""
        confidence = 0.0

        # Self-similarity is key indicator
        confidence += self_sim * 0.3

        # Fractal dimension near 1.5 is interesting
        dim_score = 1 - abs(box_dim - 1.5) / 0.5
        confidence += max(0, dim_score) * 0.2

        # Harmonic resonance
        confidence += harmonic_res * 0.3

        # Geometric structure
        if geometry.vertices > 10 and geometry.edges > 5:
            confidence += 0.1
        if geometry.sacred_geometry_match != "unknown":
            confidence += 0.1

        return min(1.0, confidence)

    def register_pattern(self, analysis: FractalAnalysis, label: str = ""):
        """Register a known pattern for future matching."""
        pattern_data = analysis.to_dict()
        pattern_data["label"] = label
        self.known_patterns_raw.append(pattern_data)

        # Persist
        pattern_file = self.storage_dir / "known_patterns.json"
        with open(pattern_file, 'w', encoding='utf-8') as f:
            json.dump({"patterns": self.known_patterns_raw}, f, indent=2)

    def find_matching_patterns(self, analysis: FractalAnalysis,
                               threshold: float = 0.7) -> List[Dict]:
        """Find known patterns that match the given analysis."""
        matches = []

        for known in self.known_patterns_raw:
            score = self._compute_match_score(analysis, known)
            if score >= threshold:
                matches.append({
                    "pattern": known,
                    "match_score": score
                })

        return sorted(matches, key=lambda x: x["match_score"], reverse=True)

    def _compute_match_score(self, analysis: FractalAnalysis, known: Dict) -> float:
        """Compute similarity score between analysis and known pattern."""
        score = 0.0
        weights = 0.0

        # Head signature match
        if analysis.head_signature == known.get("head_signature"):
            score += 1.0
            weights += 1.0

        # Self-similarity comparison
        known_sim = known.get("self_similarity", 0)
        sim_diff = abs(analysis.self_similarity - known_sim)
        score += (1 - sim_diff) * 0.5
        weights += 0.5

        # Box dimension comparison
        known_dim = known.get("box_dimension", 1.5)
        dim_diff = abs(analysis.box_dimension - known_dim)
        score += (1 - dim_diff) * 0.3
        weights += 0.3

        # Harmonic resonance comparison
        known_res = known.get("harmonic_resonance", 0)
        res_diff = abs(analysis.harmonic_resonance - known_res)
        score += (1 - res_diff) * 0.4
        weights += 0.4

        return score / weights if weights > 0 else 0


if __name__ == "__main__":
    print("Fractal Pattern Analyzer")
    print("=" * 40)

    analyzer = FractalAnalyzer()

    # Test with sample content
    test_content = b"""
    The pattern repeats at every scale.
    The pattern repeats at every scale.
    Phi ratio: 1.618 appears throughout.
    Symmetry in the structure reveals itself.
    """ * 10

    analysis = analyzer.analyze(test_content)

    print(f"\nAnalysis Results:")
    print(f"  Head entropy: {analysis.head_entropy:.3f}")
    print(f"  Self-similarity: {analysis.self_similarity:.3f}")
    print(f"  Box dimension: {analysis.box_dimension:.3f}")
    print(f"  Lacunarity: {analysis.lacunarity:.3f}")
    print(f"  Harmonic resonance: {analysis.harmonic_resonance:.3f}")
    print(f"  Pattern confidence: {analysis.pattern_confidence:.3f}")
    print(f"  Symmetry order: {analysis.geometry.symmetry_order}")
    print(f"  Golden ratio presence: {analysis.geometry.golden_ratio_presence:.3f}")
    print(f"  Sacred geometry match: {analysis.geometry.sacred_geometry_match}")
