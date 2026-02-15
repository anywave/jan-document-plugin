import pytest
import math
from coherence.network import NetworkNode, KuramotoNetwork

class TestNetworkNode:
    def test_create_node(self):
        node = NetworkNode(node_id='a', phase=0.0, natural_freq=0.1, ccs=0.5)
        assert node.node_id == 'a'

    def test_ccs_readonly_in_coupling(self):
        node = NetworkNode(node_id='a', phase=0.0, natural_freq=0.1, ccs=0.5)
        node.ccs = 0.9
        assert node.ccs == 0.9

class TestKuramotoNetwork:
    def test_empty_network(self):
        net = KuramotoNetwork(coupling_strength=0.5)
        net.step(0.1)  # Should not crash

    def test_single_node_free_runs(self):
        net = KuramotoNetwork(coupling_strength=0.5)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        net.step(0.1)
        assert net.nodes['a'].phase == pytest.approx(0.1, abs=0.01)

    def test_two_nodes_synchronize(self):
        net = KuramotoNetwork(coupling_strength=2.0)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        net.add_node(NetworkNode('b', phase=math.pi, natural_freq=1.0, ccs=0.5))
        initial_diff = abs(net.nodes['a'].phase - net.nodes['b'].phase)
        for _ in range(100):
            net.step(0.05)
        final_diff = abs(net.nodes['a'].phase - net.nodes['b'].phase) % (2 * math.pi)
        assert final_diff < initial_diff or final_diff > (2 * math.pi - 0.5)

    def test_phase_lock_score(self):
        net = KuramotoNetwork(coupling_strength=1.0)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        net.add_node(NetworkNode('b', phase=0.01, natural_freq=1.0, ccs=0.5))
        assert net.phase_lock_score() > 0.9

    def test_ccs_never_coupled(self):
        net1 = KuramotoNetwork(coupling_strength=1.0)
        net1.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.1))
        net1.add_node(NetworkNode('b', phase=1.0, natural_freq=1.0, ccs=0.1))
        net2 = KuramotoNetwork(coupling_strength=1.0)
        net2.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.9))
        net2.add_node(NetworkNode('b', phase=1.0, natural_freq=1.0, ccs=0.9))
        for _ in range(10):
            net1.step(0.1)
            net2.step(0.1)
        assert net1.nodes['a'].phase == pytest.approx(net2.nodes['a'].phase, abs=1e-10)

    def test_get_status(self):
        net = KuramotoNetwork(coupling_strength=1.0)
        net.add_node(NetworkNode('a', phase=0.0, natural_freq=1.0, ccs=0.5))
        status = net.get_status()
        assert status['node_count'] == 1
        assert 'phase_lock_score' in status
