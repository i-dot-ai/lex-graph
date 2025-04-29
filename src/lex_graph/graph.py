from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from lex_graph.types import (
    Commentary,
    FreeTextReference,
    Legislation,
    Paragraph,
    Provision,
    Schedule,
    Section,
)


class LegislationGraph:
    """
    A class to create and manage a graph representation of legislation documents.
    The graph contains nodes for legislations, sections, and paragraphs,
    and edges for references between them.
    """

    def __init__(self, granularity: str, id_mappings: dict = {}) -> None:
        """Initialize empty graph with no nodes or edges."""

        valid_granularities = ["section", "paragraph"]
        assert (
            granularity in valid_granularities
        ), f"Granularity must be one of {valid_granularities}"
        self.granularity = granularity

        # Mapping of act titles to URI ids
        self.id_mappings = id_mappings

        # Temp storage as lists for faster loading
        self.nodes_temp: List[Dict] = []
        self.edges_temp: List[Dict] = []

        # Core columns for nodes and edges
        self.core_node_columns = ["id", "label", "type", "text", "legislation_title"]
        self.core_edge_columns = ["source_id", "target_id", "type", "context"]

        # Final storage as DataFrames
        self.nodes: pd.DataFrame = pd.DataFrame(columns=self.core_node_columns)
        self.edges: pd.DataFrame = pd.DataFrame(columns=self.core_edge_columns)

    @classmethod
    def from_legislations(
        cls, legislations: List[Legislation], granularity: str
    ) -> "LegislationGraph":
        """
        Create a graph from a list of legislation objects.

        Args:
            legislations: List of legislation objects to convert into a graph
        """

        # Build a mapping of all legislation titles to their URI ids
        act_to_uri = {}
        for legislation in legislations:
            act_to_uri[legislation.title] = legislation.uri

        graph = cls(granularity=granularity, id_mappings=act_to_uri)

        print("Converting legislations to nodes and edges...")
        for legislation in tqdm(legislations):
            # Process legislation
            graph._add_legislation_node(legislation)

            # Process sections
            for section in legislation.sections:
                graph._add_section_node(section, legislation)

            # Process schedules
            for schedule in legislation.schedules:
                graph._add_schedule_node(schedule, legislation)

        # Convert temp storage to edges and nodes DataFrames
        graph.nodes = pd.DataFrame(graph.nodes_temp)
        graph.edges = pd.DataFrame(graph.edges_temp)
        graph._clear_temp_storage()

        print("\nInitial stats:")
        print(f"Nodes: {len(graph.nodes)}")
        print(f"Edges: {len(graph.edges)}\n")

        # Convert edge URIs ids to the set granularity
        graph.trim_uris_to_granularity()

        # Drop duplicate edges
        graph.drop_duplicate_edges()

        print("\nStats after cleaning:")
        print(f"Nodes: {len(graph.nodes)}")
        print(f"Edges: {len(graph.edges)}")

        return graph

    @classmethod
    def from_dataframes(
        cls, nodes: pd.DataFrame, edges: pd.DataFrame, granularity: str
    ) -> "LegislationGraph":
        """
        Load a graph from existing nodes and edges DataFrames.

        Args:
            nodes: DataFrame containing node information
            edges: DataFrame containing edge information
        """
        instance = cls(granularity=granularity)
        instance.nodes = nodes
        instance.edges = edges

        return instance

    def _add_node(self, node_data: Dict) -> None:
        """Add a node to the node list."""
        assert set(self.core_node_columns).issubset(
            node_data.keys()
        ), f"Missing node columns: {self.core_node_columns}"
        self.nodes_temp.append(node_data)

    def _add_edge(self, edge_data: Dict) -> None:
        """Add an edge to the edge list."""
        assert set(self.core_edge_columns).issubset(
            edge_data.keys()
        ), f"Missing edge columns: {self.core_edge_columns}"
        self.edges_temp.append(edge_data)

    def _clear_temp_storage(self) -> None:
        """Clear temporary storage lists."""
        self.nodes_temp = []
        self.edges_temp = []

    def _add_legislation_node(self, legislation: Legislation) -> None:
        """Add a legislation node to the node list."""
        node_data = {
            "id": legislation.id,
            "label": legislation.title,
            "type": "legislation",
            "text": legislation.description,
            "extent": [[e.value for e in legislation.extent]],
            "number_of_provisions": legislation.number_of_provisions,
            "legislation_title": legislation.title,
        }

        if legislation.title not in self.id_mappings:
            self.id_mappings[node_data["label"]] = node_data["id"]

        self._add_node(node_data)

    def _add_section_node(self, section: Section, legislation: Legislation) -> None:
        """Add a section node and its references to the graph."""

        # Add section paragraphs as nodes if granularity is paragraph
        if self.granularity == "paragraph":
            for para in section.paragraphs:
                self._add_paragraph_node(para, section)

        # Create node
        node_data = {
            "id": section.id,
            "number": section.number,
            "label": (section.text[:100] + "...")
            if len(section.text) > 100
            else section.text,
            "type": "section",
            "text": section.get_all_text()
            if self.granularity == "section"
            else section.text,
            "extent": [[e.value for e in section.extent]],
            "legislation_title": legislation.title,
        }
        self._add_node(node_data)

        # Add references and citations as edges
        self._add_provision_content_edges(section, legislation.commentaries)

        # Add hierarchy link back to parent legislation
        edge_data = {
            "source_id": section.id,
            "target_id": legislation.id,
            "type": "part_of",
            "context": "",
        }
        self._add_edge(edge_data)

    def _add_schedule_node(self, schedule: Schedule, legislation: Legislation) -> None:
        """Add a section node and its references to the graph."""

        # Add paragraphs as nodes if granularity is paragraph
        if self.granularity == "paragraph":
            for para in schedule.paragraphs:
                self._add_paragraph_node(para, schedule)

        label = schedule.text if schedule.text else f"Schedule {schedule.number}"
        if len(label) > 100:
            label = label[:100] + "..."

        # Create node
        node_data = {
            "id": schedule.id,
            "number": schedule.number,
            "label": label,
            "type": "schedule",
            "text": schedule.get_all_text()
            if self.granularity == "section"
            else schedule.text,
            "extent": [[e.value for e in schedule.extent]],
            "legislation_title": legislation.title,
        }
        self._add_node(node_data)

        # Add references and citations as edges
        self._add_provision_content_edges(schedule, legislation.commentaries)

        # Add hierarchy link back to parent legislation
        edge_data = {
            "source_id": schedule.id,
            "target_id": legislation.id,
            "type": "part_of",
            "context": "",
        }
        self._add_edge(edge_data)

    def _add_paragraph_node(self, para: Paragraph, provision: Provision) -> None:
        """Add a paragraph node and its references to the graph."""
        # Create node
        node_data = {
            "id": para.id,
            "label": f"Paragraph {para.number}",
            "type": "paragraph",
            "text": para.text,
            "provision_id": provision.id,
            "legislation_title": provision.legislation_title,
        }
        self._add_node(node_data)

        # Add references
        self._add_freetext_references(para.references)

        # Add link to parent section
        edge_data = {
            "source_id": para.id,
            "target_id": provision.id,
            "type": "part_of",
            "context": "",
        }
        self._add_edge(edge_data)

    def _add_freetext_references(self, references: List[FreeTextReference]) -> None:
        """Add reference edges to the edge list."""

        ref_edges = []
        for ref in references:
            # If Act was found, get the URI for the act
            if ref.act:
                canonical_url = self._get_act_uri(ref.act)
                if ref.section:
                    # Point URI to specific Section if it was mentioned
                    target = f"{canonical_url}/{ref.section}"
                else:
                    target = canonical_url

            # If no Act was mentioned, assume the Section is within the same legislation as the source
            elif not ref.act:
                if ref.section:
                    parts = ref.source_id.split("/")
                    type, year, number = parts[4], parts[5], parts[6]
                    if "section" in ref.context:
                        component = "section"
                    elif "schedule" in ref.context:
                        component = "schedule"
                    else:
                        component = "section"  # Default to section
                    target = f"http://www.legislation.gov.uk/id/{type}/{year}/{number}/{component}/{ref.section}"
                else:
                    print(
                        f"WARNING: FreeTextReference must have either an act or a section ({ref.source_id})"
                    )
                    continue

            # Add the reference edge to the list
            ref_edges.append(
                {
                    "source_id": ref.source_id,
                    "target_id": target,
                    "type": "freetext_reference",
                    "context": ref.context,
                }
            )

        for edge in ref_edges:
            self._add_edge(edge)

    def _add_commentary_citations(
        self, source_id: str, references: List[str], commentaries: Dict[str, Commentary]
    ) -> None:
        """Add citation edges to the edge list."""

        citation_data = []
        for commentary_ref in references:
            if commentary_ref not in commentaries:
                print(f"WARNING: Commentary not found: {commentary_ref}")
                continue

            commentary = commentaries[
                commentary_ref
            ]  # Get the actual commentary object by id
            # Add an edge for each citation in the commentary
            for citation in commentary.citations:
                citation_data.append(
                    {
                        "source_id": source_id,
                        "target_id": citation.uri,
                        "type": "commentary_"
                        + citation.type,  # https://legislation.github.io/clml-schema/userguide.html#commentaries
                        "context": citation.context,
                    }
                )

        for edge in citation_data:
            self._add_edge(edge)

    def _add_provision_content_edges(
        self, provision: Provision, commentaries: Dict[str, Commentary]
    ) -> None:
        """Add reference and citation edges to the edge list."""

        if self.granularity == "section":
            # Get all child free text references from provision
            all_references = provision.all_references
            for ref in all_references:
                ref.source_id = (
                    provision.id
                )  # Update all source ID to this provision ID
            self._add_freetext_references(all_references)
            self._add_commentary_citations(
                provision.id, provision.all_commentary_refs, commentaries
            )

        elif self.granularity == "paragraph":
            # Add references and citations from top level section only
            self._add_freetext_references(provision.references)
            self._add_commentary_citations(
                provision.id, provision.commentary_refs, commentaries
            )
        else:
            raise ValueError(f"Invalid granularity: {self.granularity}")

    def _get_act_uri(self, title: str) -> str:
        # Get the canonical URI for a UK legislation title
        if title in self.id_mappings:
            return self.id_mappings[title]
        else:
            return self._fetch_uri_from_web(title)

    @lru_cache(maxsize=100000)  # 100k to avoid repeated requests (53k unique titles)
    def _fetch_uri_from_web(self, title: str) -> str:
        """
        Fetch the canonical URI for a UK legislation title from the web.
        https://www.legislation.gov.uk/developer/uris
        """
        response = requests.get(
            f"https://www.legislation.gov.uk/id?title={title}&type=primary"
        )

        if response.status_code == 200:  # Exact match
            if "Content-Location" in response.headers:
                uri = response.headers["Content-Location"].rstrip("/contents/data.htm")
                self.id_mappings[title] = uri
                return uri
            else:
                raise ValueError(f'URI "Location" not found for title: {title}')

        elif response.status_code == 301:  # One match
            data = response.json()
            if "Location" in data:
                self.id_mappings[title] = data["Location"]  # Cache the result
                return data["Location"]
            else:
                raise ValueError(f'URI "Location" not found for title: {title}')

        elif response.status_code == 300:  # Multiple matches
            print(f"Multiple URIs found for title: {title}")

            soup = BeautifulSoup(response.text, "html.parser")
            matches = []

            # Find all links in the response
            for link in soup.find_all("a"):
                matches.append({"title": link.text.strip(), "uri": link["href"]})

            if matches:
                # For now just return the shortest string match as best
                shortest_match = min(matches, key=lambda x: len(x["title"]))
                self.id_mappings[title] = shortest_match["uri"]  # Cache the result
                return shortest_match["uri"]
            else:
                print(f"Failed to retrieve URI for title: {title}")
                return title

        else:
            # raise ValueError(f'Failed to retrieve URI for title: {title}, status code: {response.status_code}')
            print(
                f"Failed to retrieve URI for title: {title}, status code: {response.status_code}"
            )
            return title

    def trim_uris_to_granularity(self) -> None:
        """Trim all node and edge URIs to the specified granularity.

        For paragraphs, the depth is increased by 1 if the node is under a schedule,
        since schedule paragraphs have an additional URI component.
        """

        def get_depth(uri: str, base_depth: int) -> int:
            """Determine the appropriate depth based on URI structure."""
            parts = uri.split("/")
            # Check if this is a schedule URI
            if "schedule" in parts and self.granularity == "paragraph":
                return base_depth + 1
            return base_depth

        if self.granularity == "section":
            base_depth = 9
        elif self.granularity == "paragraph":
            base_depth = 10
        else:
            raise ValueError(f"Invalid granularity: {self.granularity}")

        # Trim edge source IDs
        self.edges["source_id"] = self.edges["source_id"].apply(
            lambda x: "/".join(x.split("/")[: get_depth(x, base_depth)])
            if len(x.split("/")) >= get_depth(x, base_depth)
            else x
        )

        # Trim edge target IDs
        self.edges["target_id"] = self.edges["target_id"].apply(
            lambda x: "/".join(x.split("/")[: get_depth(x, base_depth)])
            if len(x.split("/")) >= get_depth(x, base_depth)
            else x
        )

        # Trim node IDs
        self.nodes["id"] = self.nodes["id"].apply(
            lambda x: "/".join(x.split("/")[: get_depth(x, base_depth)])
            if len(x.split("/")) >= get_depth(x, base_depth)
            else x
        )

        # Remove duplicate nodes
        self.nodes = self.nodes.drop_duplicates(subset=["id", "type"])

    def drop_duplicate_edges(self) -> None:
        """Remove duplicate edges from the edge list."""
        print(f"Edges before dropping duplicates: {len(self.edges)}")
        self.edges = self.edges.drop_duplicates(
            subset=["source_id", "target_id", "type"]
        )
        print(f"Edges after dropping duplicates: {len(self.edges)}")

    def add_nodes(self, nodes: pd.DataFrame) -> None:
        """Add nodes to the graph."""
        self.nodes = pd.concat([self.nodes, nodes], ignore_index=True)

    def add_edges(self, edges: pd.DataFrame) -> None:
        """Add edges to the graph."""
        self.edges = pd.concat([self.edges, edges], ignore_index=True)

    def get_node_types(self) -> List[str]:
        """Return a list of unique node types in the graph."""
        return self.nodes["type"].unique().tolist()

    def get_edge_types(self) -> List[str]:
        """Return a list of unique edge types in the graph."""
        return self.edges["type"].unique().tolist()

    def get_subgraph(
        self, node_types: List[str] = [], edge_types: List[str] = []
    ) -> "LegislationGraph":
        """
        Return a subgraph containing only specified node and edge types.

        Args:
            node_types: List of node types to include. If None, include all.
            edge_types: List of edge types to include. If None, include all.

        Returns:
            tuple: (nodes DataFrame, edges DataFrame)
        """
        nodes = self.nodes
        edges = self.edges

        if len(node_types) > 0:
            nodes = nodes[nodes["type"].isin(node_types)]
        if len(edge_types) > 0:
            edges = edges[edges["type"].isin(edge_types)]

        # Only keep edges where both source and target nodes exist
        valid_nodes = nodes["id"].tolist()
        edges = edges[
            edges["source_id"].isin(valid_nodes) & edges["target_id"].isin(valid_nodes)
        ]

        return LegislationGraph.from_dataframes(nodes, edges, self.granularity)

    def drop_invalid_edges(self) -> None:
        """Remove edges where the source or target node is not in the node list."""
        valid_nodes = self.nodes["id"].tolist()
        self.edges = self.edges[
            self.edges["source_id"].isin(valid_nodes)
            & self.edges["target_id"].isin(valid_nodes)
        ]

    def drop_isolated_nodes(self) -> None:
        """Remove nodes that have no edges."""
        valid_nodes = set(self.edges["source_id"]).union(set(self.edges["target_id"]))
        self.nodes = self.nodes[self.nodes["id"].isin(valid_nodes)]

    def print_summary(self) -> None:
        """Print a summary of the graph."""
        print("#" * 50)
        print("Graph Summary:\n")

        # Number of nodes and edges
        print(f"Nodes: {len(self.nodes)}")
        print(f"Edges: {len(self.edges)}\n")

        # Check for disconnected nodes or invalid edges
        source_nodes = set(self.edges["source_id"])
        target_nodes = set(self.edges["target_id"])
        disconnected_nodes = set(self.nodes["id"]) - source_nodes.union(target_nodes)
        print(f"Disconnected nodes: {len(disconnected_nodes)}")

        # Check for invalid edges that have nodes not in the node list
        invalid_edges = self.edges[
            ~self.edges["source_id"].isin(self.nodes["id"])
            | ~self.edges["target_id"].isin(self.nodes["id"])
        ]
        print(f"Invalid edges (unknown node): {len(invalid_edges)}\n")
        if len(invalid_edges) > 0:
            print("Invalid Edge Node Type Distribution:")
            print(invalid_edges["type"].value_counts())

            print("\nUnkown Edge Node Sample:")
            print(invalid_edges.sample(10).target_id)

        # Node and edge types
        print(f"\nNode Types: {self.nodes.value_counts('type')}\n")
        print(f"Edge Types: {self.edges.value_counts('type')}\n")

        # Degree stats
        out_degree = self.edges["source_id"].value_counts()
        in_degree = self.edges["target_id"].value_counts()
        full_degree = out_degree.add(in_degree, fill_value=0)
        degree_stats = full_degree.describe()
        print(f"Degree Stats:\n{degree_stats}\n")

        print("Highest Degree Nodes:")
        print(full_degree.nlargest(5))
        print()

        # Print recall statistics - TODO Need to figure out what constitutes a provision
        print("Data Recall Statistics:")
        total_provisions = self.nodes[self.nodes["type"] == "legislation"][
            "number_of_provisions"
        ].sum()
        print("Number of provisions (metadata): ", total_provisions)
        print(
            "Number of provisions (nodes): ",
            len(self.nodes[self.nodes["type"] != "legislation"]),
        )
        percentage_provisions = (
            (len(self.nodes) / total_provisions) * 100 if total_provisions > 0 else 0
        )
        print(
            f"Difference in number of provisions: {total_provisions - len(self.nodes)} ({percentage_provisions:.2f}%)"
        )

        print("#" * 50)

    def save(self, output_path: str) -> None:
        """Save the graph to CSV files."""

        # Create output directory if it doesn't exist
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        self.nodes.to_csv(f"{output_path}/nodes.tsv", sep="\t", index=True)
        self.edges.to_csv(f"{output_path}/edges.tsv", sep="\t", index=True)

    def save_edgelist(self, output_path: str) -> None:
        """Save the graph to an edge list file."""

        # Create output directory if it doesn't exist
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        self.edges[["source_id", "target_id", "type"]].to_csv(
            f"{output_path}/edgelist.tsv", sep="\t", index=False
        )
        self.nodes[["id", "label", "type"]].to_csv(
            f"{output_path}/nodelist.tsv", sep="\t", index=False
        )

    def save_neo4j(self, output_path: str) -> None:
        """
        Save the graph to Neo4j-optimized TSV files following Neo4j's recommended import format.
        This format creates separate files for each node and relationship type,
        organized in dedicated subdirectories.

        Args:
            output_path: Path to save the files to
        """
        # Create output directory if it doesn't exist
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories for nodes and relationships
        nodes_dir = output_path / "nodes"
        nodes_dir.mkdir(exist_ok=True)

        rels_dir = output_path / "relationships"
        rels_dir.mkdir(exist_ok=True)

        # Create separate files for each node type
        node_types = self.get_node_types()

        print(f"Creating {len(node_types)} node type files in {nodes_dir}...")

        for node_type in node_types:
            # Filter nodes by type
            type_nodes = self.nodes[self.nodes["type"] == node_type].copy()

            # Create a file for this node type
            filename = nodes_dir / f"{node_type}_nodes.tsv"

            # Add :ID label to id column and :LABEL for Neo4j label
            # Use a copy to avoid modifying the original dataframe
            export_df = type_nodes.copy()

            # Rename 'id' column to ':ID' for Neo4j import
            headers = export_df.columns.tolist()
            headers[headers.index("id")] = ":ID"

            # Add a :LABEL column with the node type
            export_df[":LABEL"] = node_type.capitalize()
            headers.append(":LABEL")

            # Export to TSV
            export_df.to_csv(
                filename,
                sep="\t",
                index=False,
                header=headers,
                escapechar="\\",
                quoting=3,  # QUOTE_NONE
                na_rep="",
            )

            print(f"  - Created {node_type} nodes file with {len(export_df)} rows")

        # Create separate files for each edge type
        edge_types = self.get_edge_types()

        print(f"Creating {len(edge_types)} relationship type files in {rels_dir}...")

        for edge_type in edge_types:
            # Filter edges by type
            type_edges = self.edges[self.edges["type"] == edge_type].copy()

            # Skip if no edges of this type
            if len(type_edges) == 0:
                continue

            # Create a file for this relationship type
            filename = rels_dir / f"{edge_type}_relationships.tsv"

            # Rename columns for Neo4j import
            type_edges.rename(
                columns={
                    "source_id": ":START_ID",
                    "target_id": ":END_ID",
                    "type": ":TYPE",
                },
                inplace=True,
            )

            # Export to TSV
            type_edges.to_csv(
                filename,
                sep="\t",
                index=False,
                escapechar="\\",
                quoting=3,  # QUOTE_NONE
                na_rep="",
            )

            print(
                f"  - Created {edge_type} relationships file with {len(type_edges)} rows"
            )

        # Create a Neo4j import command example file
        with open(f"{output_path}/import_command.txt", "w") as f:
            f.write("# Neo4j Import Command Example:\n\n")
            f.write("neo4j-admin import \\\n")

            # Add node files to command with subdirectory paths
            for node_type in node_types:
                f.write(f"  --nodes={node_type}=nodes/{node_type}_nodes.tsv \\\n")

            # Add relationship files to command with subdirectory paths
            for edge_type in edge_types:
                if len(self.edges[self.edges["type"] == edge_type]) > 0:
                    f.write(
                        f"  --relationships={edge_type}=relationships/{edge_type}_relationships.tsv \\\n"
                    )

            f.write('  --delimiter="\\t" \\\n')
            f.write('  --array-delimiter=";" \\\n')
            f.write("  --skip-bad-relationships=true \\\n")
            f.write("  --skip-duplicate-nodes=true \\\n")
            f.write("  --id-type=STRING \n")

        print(f"\nGraph saved in Neo4j-optimized TSV format to {output_path}")
        print(f"Nodes saved in: {nodes_dir}")
        print(f"Relationships saved in: {rels_dir}")
        print(f"Created import command example in {output_path}/import_command.txt")
