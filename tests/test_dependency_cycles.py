from src.dependencies import find_cycle_if_added, find_path


def test_find_path_direct_and_indirect():
    edges = [(3, 2), (2, 1)]

    assert find_path(edges, 3, 2) == [3, 2]
    assert find_path(edges, 3, 1) == [3, 2, 1]


def test_find_path_none_when_not_connected():
    edges = [(3, 2), (2, 1)]

    assert find_path(edges, 1, 3) is None      # wrong direction
    assert find_path(edges, 3, 9) is None
    assert find_path([], 1, 2) is None


def test_find_path_prefers_the_shortest_chain():
    edges = [(4, 3), (3, 2), (2, 1), (4, 1)]

    assert find_path(edges, 4, 1) == [4, 1]


def test_find_path_handles_diamonds_and_existing_loops_without_hanging():
    diamond = [(4, 2), (4, 3), (2, 1), (3, 1)]
    loop = [(1, 2), (2, 1), (3, 1)]

    assert find_path(diamond, 4, 1) in ([4, 2, 1], [4, 3, 1])
    assert find_path(loop, 3, 9) is None


def test_safe_new_links_return_none():
    edges = [(2, 1)]

    assert find_cycle_if_added(edges, 3, 2) is None
    assert find_cycle_if_added(edges, 3, 1) is None
    assert find_cycle_if_added([], 1, 2) is None


def test_self_dependency_is_a_cycle():
    assert find_cycle_if_added([], 4, 4) == [4, 4]


def test_direct_reverse_link_is_a_cycle():
    assert find_cycle_if_added([(2, 1)], 1, 2) == [1, 2, 1]


def test_indirect_loop_reports_the_whole_chain():
    edges = [(3, 2), (2, 1)]

    assert find_cycle_if_added(edges, 1, 3) == [1, 3, 2, 1]


def test_unrelated_branches_do_not_trigger_false_loops():
    edges = [(2, 1), (4, 3)]

    assert find_cycle_if_added(edges, 3, 2) is None
    assert find_cycle_if_added(edges, 1, 4) is None
