from pathlib import Path

import pandas as pd
import pytest

from lex_graph.graph import LegislationGraph
from scripts.preprocess import LegislationProcessor


@pytest.fixture
def sample_legislation():
    processor = LegislationProcessor(
        input_path="tests/test_data/raw", output_path="tests/test_data/processed"
    )
    legislation = processor.process_file(
        Path("tests/test_data/raw/housing_act_sample.xml")
    )
    return legislation


def test_legislation_graph_initialization():
    graph = LegislationGraph(granularity="section")
    assert graph.granularity == "section"
    assert graph.nodes.empty
    assert graph.edges.empty


def test_legislation_graph_from_legislations(sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="section"
    )
    print(graph.edges)
    assert not graph.nodes.empty
    assert not graph.edges.empty
    assert len(graph.nodes) == 3  # legislation, section, schedule
    assert len(graph.edges) >= 15  # section to legislation, schedule to legislation


def test_legislation_graph_from_legislations_paragraph(sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="paragraph"
    )
    print(graph.edges)
    assert not graph.nodes.empty
    assert not graph.edges.empty
    assert (
        len(graph.nodes) == 7
    )  # legislation, section, schedule, section1para1, section1para2, section1para3, schedule1para1
    assert len(graph.edges) >= 20  # section to legislation, schedule to legislation,


def test_legislation_graph_from_dataframes():
    nodes = pd.DataFrame(
        [
            {
                "id": "node1",
                "label": "Node 1",
                "type": "legislation",
                "text": "Node 1 text",
                "legislation_title": "Node 1",
            }
        ]
    )
    edges = pd.DataFrame(
        [
            {
                "source_id": "node1",
                "target_id": "node2",
                "type": "reference",
                "context": "",
            }
        ]
    )
    graph = LegislationGraph.from_dataframes(nodes, edges, granularity="section")
    assert not graph.nodes.empty
    assert not graph.edges.empty
    assert len(graph.nodes) == 1
    assert len(graph.edges) == 1


def test_add_node():
    graph = LegislationGraph(granularity="section")
    node_data = {
        "id": "node1",
        "label": "Node 1",
        "type": "legislation",
        "text": "Node 1 text",
        "legislation_title": "Node 1",
    }
    graph._add_node(node_data)
    assert len(graph.nodes_temp) == 1


def test_add_edge():
    graph = LegislationGraph(granularity="section")
    edge_data = {
        "source_id": "node1",
        "target_id": "node2",
        "type": "reference",
        "context": "",
    }
    graph._add_edge(edge_data)
    assert len(graph.edges_temp) == 1


def test_clear_temp_storage():
    graph = LegislationGraph(granularity="section")
    graph.nodes_temp.append({"id": "node1"})
    graph.edges_temp.append({"source_id": "node1", "target_id": "node2"})
    graph._clear_temp_storage()
    assert len(graph.nodes_temp) == 0
    assert len(graph.edges_temp) == 0


def test_trim_uris_to_granularity_section():
    graph = LegislationGraph(granularity="section")
    print(
        "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1".split(
            "/"
        )
    )
    print(
        "http://www.legislation.gov.uk/id/ukpga/2004/34/schedule/1/paragraph/1".split(
            "/"
        )
    )
    graph.nodes = pd.DataFrame(
        [
            {
                "id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "type": "paragraph",
            }
        ]
    )
    graph.edges = pd.DataFrame(
        [
            {
                "source_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "target_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/2/paragraph2",
                "type": "part_of",
            }
        ]
    )
    graph.trim_uris_to_granularity()
    assert (
        graph.nodes.iloc[0]["id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1"
    )
    assert (
        graph.edges.iloc[0]["source_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1"
    )
    assert (
        graph.edges.iloc[0]["target_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/2"
    )


def test_trim_uris_to_granularity_schedule():
    # Schedules have different URI structure
    graph = LegislationGraph(granularity="section")
    graph.nodes = pd.DataFrame(
        [
            {
                "id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1/paragraph/1",
                "type": "schedule",
            },
            {
                "id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "type": "section",
            },
        ]
    )
    graph.edges = pd.DataFrame(
        [
            {
                "source_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1/paragraph/1",
                "target_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "type": "citation",
            }
        ]
    )
    graph.trim_uris_to_granularity()
    assert (
        graph.nodes.iloc[0]["id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1"
    )
    assert (
        graph.edges.iloc[0]["source_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1"
    )
    assert (
        graph.edges.iloc[0]["target_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1"
    )


def test_trim_uris_to_granularity_schedule_paragraph():
    # Schedules have different URI structure
    graph = LegislationGraph(granularity="paragraph")
    graph.nodes = pd.DataFrame(
        [
            {
                "id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1/paragraph/1",
                "type": "schedule",
            },
            {
                "id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "type": "section",
            },
        ]
    )
    graph.edges = pd.DataFrame(
        [
            {
                "source_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1/paragraph/1",
                "target_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "type": "citation",
            }
        ]
    )
    graph.trim_uris_to_granularity()
    assert (
        graph.nodes.iloc[0]["id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1/paragraph/1"
    )
    assert (
        graph.edges.iloc[0]["source_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/schedule/1/paragraph/1"
    )
    assert (
        graph.edges.iloc[0]["target_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1"
    )


def test_trim_uris_to_granularity_paragraph():
    graph = LegislationGraph(granularity="paragraph")
    graph.nodes = pd.DataFrame(
        [
            {
                "id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "type": "paragraph",
            }
        ]
    )
    graph.edges = pd.DataFrame(
        [
            {
                "source_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1",
                "target_id": "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/2/paragraph2",
                "type": "part_of",
            }
        ]
    )
    graph.trim_uris_to_granularity()
    assert (
        graph.nodes.iloc[0]["id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1"
    )
    assert (
        graph.edges.iloc[0]["source_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/1/paragraph1"
    )
    assert (
        graph.edges.iloc[0]["target_id"]
        == "http://www.legislation.gov.uk/id/ukpga/year/leg1/section/2/paragraph2"
    )


def test_drop_duplicate_edges():
    graph = LegislationGraph(granularity="section")
    graph.edges = pd.DataFrame(
        [
            {"source_id": "node1", "target_id": "node2", "type": "reference"},
            {"source_id": "node1", "target_id": "node2", "type": "reference"},
        ]
    )
    graph.drop_duplicate_edges()
    assert len(graph.edges) == 1


def test_add_nodes():
    graph = LegislationGraph(granularity="section")
    nodes = pd.DataFrame(
        [
            {
                "id": "node1",
                "label": "Node 1",
                "type": "legislation",
                "text": "Node 1 text",
                "legislation_title": "Node 1",
            }
        ]
    )
    graph.add_nodes(nodes)
    assert len(graph.nodes) == 1


def test_add_edges():
    graph = LegislationGraph(granularity="section")
    edges = pd.DataFrame(
        [
            {
                "source_id": "node1",
                "target_id": "node2",
                "type": "reference",
                "context": "",
            }
        ]
    )
    graph.add_edges(edges)
    assert len(graph.edges) == 1


def test_get_node_types(sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="section"
    )
    node_types = graph.get_node_types()
    assert "legislation" in node_types
    assert "section" in node_types
    assert "schedule" in node_types


def test_get_edge_types(sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="section"
    )
    edge_types = graph.get_edge_types()
    assert "part_of" in edge_types


def test_get_subgraph(sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="section"
    )
    subgraph = graph.get_subgraph(
        node_types=["legislation", "section"], edge_types=["part_of"]
    )
    assert len(subgraph.nodes) == 2
    assert len(subgraph.edges) == 1


def test_drop_invalid_edges():
    graph = LegislationGraph(granularity="section")
    graph.nodes = pd.DataFrame([{"id": "node1"}])
    graph.edges = pd.DataFrame(
        [
            {"source_id": "node1", "target_id": "node2", "type": "reference"},
            {"source_id": "node1", "target_id": "node1", "type": "reference"},
        ]
    )
    graph.drop_invalid_edges()
    assert len(graph.edges) == 1


def test_drop_isolated_nodes():
    graph = LegislationGraph(granularity="section")
    graph.nodes = pd.DataFrame([{"id": "node1"}, {"id": "node2"}])
    graph.edges = pd.DataFrame(
        [{"source_id": "node1", "target_id": "node2", "type": "reference"}]
    )
    graph.drop_isolated_nodes()
    assert len(graph.nodes) == 2


def test_save(tmp_path, sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="section"
    )
    output_path = tmp_path / "output"
    output_path.mkdir()
    graph.save(output_path)
    assert (output_path / "nodes.tsv").exists()
    assert (output_path / "edges.tsv").exists()


def test_save_neo4j(tmp_path, sample_legislation):
    graph = LegislationGraph.from_legislations(
        [sample_legislation], granularity="section"
    )
    output_path = tmp_path / "output"
    output_path.mkdir()
    graph.save_neo4j(output_path)

    # check _nodes.tsv files have been created
    assert len(list(output_path.glob("nodes/*_nodes.tsv"))) > 0

    # check _relationships.tsv files have been created
    assert len(list(output_path.glob("relationships/*_relationships.tsv"))) > 0
