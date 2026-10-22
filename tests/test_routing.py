"""T3 (synchronous propagation), T4 (request rules), T5 (no knowledge state in routing).

docs/03 step 4, docs/09 engine.route. `round` is 1-based, as in docs/03 (r = 1..R).
"""
import inspect
import math

import numpy as np

from classroom_swarm.engine import Packet, route
from classroom_swarm.graphs import generate_er
from classroom_swarm.rng import weighted_pick

SRC = Packet(answer_id="h1-s0", root=0, depth=0, items=(True, False, True))


def _U(rows):
    return np.array(rows, dtype=float)


def test_no_relay_within_the_round_of_receipt():
    # path 0-1-2; 0 holds. Round 1: 1 asks 0 (transfer); 2 asks 1, which has nothing AT ROUND START.
    neighbors = ((1,), (0, 2), (1,))
    res = route(neighbors, {0: SRC}, [1, 2], _U([[0.0, 0.0, 0.0]]))
    assert 1 in res.received and 2 not in res.received
    assert sorted(res.requests) == [(1, 1, 0, True), (1, 2, 1, False)]


def test_multi_hop_needs_one_round_per_hop():
    # 0-1-2-3; 0 holds. Round 1: 1->0 (hit), 2->3 (miss), 3->2 (miss). Round 2: 2->1 (hit, 1 got it in round 1).
    neighbors = ((1,), (0, 2), (1, 3), (2,))
    U = _U([[0.0, 0.0, 0.9, 0.0], [0.0, 0.0, 0.0, 0.0]])
    res = route(neighbors, {0: SRC}, [1, 2, 3], U)
    p1, sender1, round1 = res.received[1]
    p2, sender2, round2 = res.received[2]
    assert (sender1, round1, p1.depth) == (0, 1, 1)
    assert (sender2, round2, p2.depth) == (1, 2, 2)
    for p in (p1, p2):  # exact inheritance
        assert (p.answer_id, p.root, p.items) == (SRC.answer_id, SRC.root, SRC.items)
    assert 3 not in res.received  # its only neighbour was asked in round 1, before it held anything
    assert sorted(res.requests) == [(1, 1, 0, True), (1, 2, 3, False), (1, 3, 2, False), (2, 2, 1, True)]
    assert res.incoming == {0: {1}, 3: {2}, 2: {3}, 1: {2}}

    one_round = route(neighbors, {0: SRC}, [1, 2, 3], U[:1])  # R = 1: depth never exceeds 1
    assert set(one_round.received) == {1} and one_round.received[1][0].depth == 1


def test_simultaneous_requests_to_one_holder_are_all_served():
    neighbors = ((1, 2, 3), (0,), (0,), (0,))
    res = route(neighbors, {0: SRC}, [1, 2, 3], _U([[0.5, 0.5, 0.5, 0.5]]))
    assert set(res.received) == {1, 2, 3}
    assert res.incoming == {0: {1, 2, 3}}


def test_route_signature_carries_no_knowledge_state():
    params = list(inspect.signature(route).parameters)
    assert params == ["neighbors", "holders", "copiers", "U_routing", "neighbor_weights"]


def test_T26_weighted_route_uses_same_uniform_and_uniform_weights_are_exact():
    # Student 0 asks among sorted [1, 2]. u=.5 selects 2 with uniform weights, but 1 with weights 9:1.
    neighbors = ((1, 2), (0,), (0,))
    U = _U([[0.5, 0.0, 0.0]])
    uniform = route(neighbors, {1: SRC, 2: SRC}, [0], U)
    explicit_uniform = route(neighbors, {1: SRC, 2: SRC}, [0], U,
                             ((1.0, 1.0), (1.0,), (1.0,)))
    weighted = route(neighbors, {1: SRC, 2: SRC}, [0], U,
                     ((9.0, 1.0), (9.0,), (1.0,)))
    assert uniform.requests == explicit_uniform.requests == [(1, 0, 2, True)]
    assert weighted.requests == [(1, 0, 1, True)]


def test_randomised_request_rules():
    rng = np.random.default_rng(99)
    for case in range(300):
        g = generate_er(12, 3, seed=case)
        roles = rng.random(g.N)
        holders = {i: Packet(f"h1-s{i}", i, 0, (bool(i % 2),)) for i in range(g.N) if roles[i] < 0.4}
        copiers = [i for i in range(g.N) if i not in holders]
        R = int(rng.integers(1, 5))
        U = rng.random((R, g.N))
        res = route(g.neighbors, holders, copiers, U)

        got_round = {i: rnd for i, (_, _, rnd) in res.received.items()}
        queried = {i: [] for i in copiers}
        by_round = sorted(res.requests)
        for rnd, requester, target, had in by_round:
            assert requester in copiers
            assert got_round.get(requester, math.inf) >= rnd          # stops once it has a packet
            remaining = sorted(set(g.neighbors[requester]) - set(queried[requester]))
            all_weights = g.neighbor_weights[requester]
            weight_by_neighbor = dict(zip(g.neighbors[requester], all_weights))
            expected = weighted_pick(remaining, [weight_by_neighbor[j] for j in remaining], U[rnd - 1, requester])
            assert target == expected
            queried[requester].append(target)
            holds_at_start = target in holders or got_round.get(target, math.inf) < rnd
            assert had == holds_at_start                                # T3: only round-start holders
        for i in copiers:
            asked = len(queried[i])
            if i not in res.received:
                assert asked == min(R, len(g.neighbors[i]))           # asks every round until exhausted
            else:
                packet, sender, rnd = res.received[i]
                assert (rnd, i, sender, True) in by_round
                src = holders.get(sender) or res.received[sender][0]
                assert (packet.answer_id, packet.root, packet.items) == (src.answer_id, src.root, src.items)
                assert packet.depth == src.depth + 1 <= R
        incoming = {}
        for _, requester, target, _ in res.requests:
            incoming.setdefault(target, set()).add(requester)
        assert res.incoming == incoming
