import pandas as pd
import pytest
from igraph import Graph

# Import the functions to test
from demo.app import build_graph, preprocess_graph, select_graph


@pytest.fixture
def sample_data():
    """Create sample nodes and edges dataframes for testing"""
    nodes = pd.DataFrame(
        {
            "id": [
                "act1",
                "act2",
                "section1",
                "section2",
                "section3",
                "schedule1",
                "schedule2",
            ],
            "type": [
                "legislation",
                "legislation",
                "section",
                "section",
                "section",
                "schedule",
                "schedule",
            ],
            "label": [
                "Housing Act",
                "Planning Act",
                "Section 1",
                "Section 2",
                "Section 3",
                "Schedule 1",
                "Schedule 2",
            ],
            "legislation_title": [
                "Housing Act",
                "Planning Act",
                "Housing Act",
                "Planning Act",
                "Housing Act",
                "Planning Act",
                "Housing Act",
            ],
            "text": [
                "Act text 1",
                "Act text 2",
                "Section text 1",
                "Section text 2",
                "Section text 3",
                "Schedule text 1",
                "Schedule text 2",
            ],
            "extent": ["UK", "England", "UK", "England", "UK", "England", "UK"],
        }
    )

    edges = pd.DataFrame(
        {
            "source_id": [
                "act1",
                "act1",
                "act2",
                "section1",
                "section2",
                "schedule1",
                "act1",
            ],
            "target_id": [
                "section1",
                "section2",
                "section2",
                "section3",
                "schedule1",
                "schedule2",
                "schedule2",
            ],
            "type": [
                "part_of",
                "commentary_F",
                "freetext_reference",
                "cites",
                "refers",
                "amends",
                "part_of",
            ],
            "size": [1, 1, 1, 1, 1, 1, 1],
        }
    )

    return nodes, edges


def test_base_graph_creation(sample_data):
    """Verify the base graph is created correctly"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)
    assert isinstance(g, Graph)
    assert g.vcount() == 7  # Number of nodes in sample data
    assert g.ecount() == 7  # Number of edges in sample data


@pytest.mark.parametrize("n_community,resolution", [(1, 0.1), (1, 0.5), (2, 0.1)])
def test_nth_largest_community_parameters(sample_data, n_community, resolution):
    """Test nth largest community selection with different n values and resolutions"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    result = select_graph(
        g, method="nth_largest_community", n=n_community, resolution=resolution
    )

    assert isinstance(result, Graph)
    assert result.vcount() <= g.vcount()
    assert result.ecount() <= g.ecount()


def test_nth_largest_community_too_large_n(sample_data):
    """Test behavior when requesting a community index larger than available"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    # Request 100th largest community (should return empty graph)
    result = select_graph(g, method="nth_largest_community", n=100, resolution=0.1)
    assert isinstance(result, Graph)
    assert result.vcount() == 0  # Should return empty graph


@pytest.mark.parametrize(
    "invalid_input",
    [
        {
            "method": "egonet",
            "ego_node_labels": None,
            "n_hops": 1,
        },  # Missing ego_node_labels
        {
            "method": "egonet",
            "ego_node_labels": [],
            "n_hops": 1,
        },  # Empty ego_node_labels
        {
            "method": "egonet",
            "ego_node_labels": ["Housing Act"],
            "n_hops": 0,
        },  # Invalid n_hops
        {
            "method": "egonet",
            "ego_node_labels": ["Housing Act"],
            "n_hops": -1,
        },  # Negative n_hops
        {"method": "nth_largest_component", "n": 0},  # Invalid n
        {"method": "nth_largest_component", "n": -1},  # Negative n
        {
            "method": "nth_largest_community",
            "n": 1,
            "resolution": 0,
        },  # Invalid resolution
        {
            "method": "nth_largest_community",
            "n": 1,
            "resolution": -1,
        },  # Negative resolution
    ],
)
def test_invalid_parameters(sample_data, invalid_input):
    """Test handling of various invalid parameters"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    with pytest.raises(ValueError):
        select_graph(g, **invalid_input)


def test_nonexistent_ego_nodes(sample_data):
    """Test handling of nonexistent ego nodes"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    # Should return empty graph for nonexistent nodes
    result = select_graph(
        g, method="egonet", ego_node_labels=["Nonexistent Act"], n_hops=1
    )
    assert isinstance(result, Graph)
    assert result.vcount() == 0


def test_mixed_existing_nonexisting_ego_nodes(sample_data):
    """Test handling of mix of existing and nonexistent ego nodes"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    result = select_graph(
        g, method="egonet", ego_node_labels=["Housing Act", "Nonexistent Act"], n_hops=1
    )
    assert isinstance(result, Graph)
    assert result.vcount() > 0  # Should still return graph with existing nodes


@pytest.mark.parametrize("n_hops", [1, 2])
def test_valid_ego_network_sizes(sample_data, n_hops):
    """Test that ego networks with more hops include more or equal nodes"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    one_hop = select_graph(
        g, method="egonet", ego_node_labels=["Housing Act"], n_hops=1
    )
    n_hop = select_graph(
        g, method="egonet", ego_node_labels=["Housing Act"], n_hops=n_hops
    )

    if n_hops > 1:
        assert n_hop.vcount() >= one_hop.vcount()


def test_giant_component_integrity(sample_data):
    """Test that giant component selection maintains graph integrity"""
    nodes, edges = preprocess_graph(*sample_data)
    g = build_graph(nodes, edges)

    result = select_graph(g, method="giant_component")
    assert isinstance(result, Graph)
    assert result.is_connected()  # Giant component should be connected
    assert result.vcount() <= g.vcount()
    assert result.ecount() <= g.ecount()
