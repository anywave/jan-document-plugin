"""
Kuramoto Network Phase Coupling for the MOBIUS coherence engine.

Implements a Kuramoto oscillator network where nodes couple through
phase differences. The order parameter r measures global synchronization.

CRITICAL: CCS (Composite Coherence Score) is stored on nodes for
informational purposes but NEVER enters phase coupling math.
The step() method only uses phase and natural_freq.

(c) 2026 Anywave Creations
MIT License
"""

import math
from dataclasses import dataclass


@dataclass
class NetworkNode:
    """A single oscillator node in the Kuramoto network.

    Attributes:
        node_id: Unique identifier for this node.
        phase: Current phase in radians.
        natural_freq: Natural angular frequency in rad/s.
        ccs: Composite Coherence Score. Read-only for coupling —
             stored for info, NEVER used in phase coupling math.
    """
    node_id: str
    phase: float
    natural_freq: float
    ccs: float


class KuramotoNetwork:
    """Kuramoto model network with global coupling.

    Implements the classic Kuramoto update rule:
        dphi_i/dt = omega_i + (K/N) * SUM_j sin(phi_j - phi_i)

    All phase updates are computed simultaneously (not sequentially),
    then applied in batch to avoid order-dependent drift.
    """

    def __init__(self, coupling_strength: float = 0.5):
        self.nodes: dict[str, NetworkNode] = {}
        self.coupling_strength: float = coupling_strength

    def add_node(self, node: NetworkNode) -> None:
        """Add a node to the network."""
        self.nodes[node.node_id] = node

    def remove_node(self, node_id: str) -> None:
        """Remove a node from the network by ID."""
        self.nodes.pop(node_id, None)

    def step(self, dt: float) -> None:
        """Advance the network by dt seconds using Kuramoto dynamics.

        Computes ALL phase derivatives first, THEN applies them
        simultaneously to avoid sequential update bias.

        CCS is deliberately excluded from this computation.
        Only phase and natural_freq participate.
        """
        n = len(self.nodes)
        if n == 0:
            return

        # Compute all deltas first (simultaneous update)
        deltas: dict[str, float] = {}
        node_list = list(self.nodes.values())

        for node_i in node_list:
            coupling_sum = 0.0
            for node_j in node_list:
                if node_j.node_id != node_i.node_id:
                    coupling_sum += math.sin(node_j.phase - node_i.phase)

            dphi = node_i.natural_freq + (self.coupling_strength / n) * coupling_sum
            deltas[node_i.node_id] = dphi * dt

        # Apply all updates at once
        for node_id, delta in deltas.items():
            self.nodes[node_id].phase += delta

    def phase_lock_score(self) -> float:
        """Compute the Kuramoto order parameter r.

        r = |1/N * SUM_k exp(i * phi_k)|

        Returns:
            1.0 for perfect synchronization, 0.0 for no coherence.
            Returns 0.0 for an empty network.
        """
        n = len(self.nodes)
        if n == 0:
            return 0.0

        real_sum = 0.0
        imag_sum = 0.0
        for node in self.nodes.values():
            real_sum += math.cos(node.phase)
            imag_sum += math.sin(node.phase)

        real_sum /= n
        imag_sum /= n

        return math.sqrt(real_sum * real_sum + imag_sum * imag_sum)

    def get_status(self) -> dict:
        """Return a status dict describing the current network state."""
        return {
            'node_count': len(self.nodes),
            'coupling_strength': self.coupling_strength,
            'phase_lock_score': self.phase_lock_score(),
            'nodes': {
                nid: {
                    'phase': node.phase,
                    'natural_freq': node.natural_freq,
                    'ccs': node.ccs,
                }
                for nid, node in self.nodes.items()
            },
        }

    def reset(self) -> None:
        """Clear all nodes from the network."""
        self.nodes.clear()
