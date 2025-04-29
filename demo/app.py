import random

import matplotlib
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from igraph import Graph

# Set page configuration
st.set_page_config(page_title="Graph Visualization App", layout="wide")


def display_graph_metrics(graph):
    """Display various metrics about the graph"""
    st.subheader("Graph Metrics")
    st.write(f"Total Nodes: {graph.vcount()}")
    st.write(f"Total Edges: {graph.ecount()}")
    st.write(f"Graph Density: {graph.density():.3f}")
    st.write(f"Average Degree: {2 * graph.ecount() / graph.vcount():.2f}")

    # Most connected nodes
    degree_sequence = graph.degree()
    max_degree = max(degree_sequence)
    max_degree_vertices = [v.index for v in graph.vs if graph.degree(v) == max_degree]
    st.write(
        f"Most Connected Node(s) (Degree {max_degree}): "
        f"{', '.join(str(graph.vs[v]['id']) for v in max_degree_vertices)}"
    )

    # Component information
    components = graph.components()
    st.write(f"Number of Connected Components: {len(components)}")
    st.write(f"Size of Largest Component: {max(len(c) for c in components)}")

    if graph.is_connected():
        st.write(f"Average Path Length: {graph.average_path_length():.2f}")


# Caching data loading
@st.cache_data(ttl=3600, show_spinner=True)
def load_data():
    base_path = "data/graph"
    edges_path = f"{base_path}/edges.csv"
    nodes_path = f"{base_path}/nodes.csv"

    try:
        edges_all = pd.read_csv(edges_path)
        nodes_all = pd.read_csv(nodes_path)
        return nodes_all, edges_all
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return None, None


@st.cache_data
def preprocess_graph(nodes, edges):
    """Preprocess graph data with proper error handling"""
    try:
        # Drop rows with missing values
        edges = edges.dropna(subset=["source_id", "target_id"])

        # Drop duplicates
        edges = edges.drop_duplicates(subset=["source_id", "target_id", "type"])

        # Reset node indices
        nodes = nodes.reset_index(drop=True)

        # Create node ID mapping
        idx_map = pd.Series(range(len(nodes)), index=nodes["id"]).to_dict()

        # Handle missing nodes
        all_ids = set(edges["source_id"]).union(set(edges["target_id"]))
        missing_ids = all_ids - set(idx_map.keys())

        # Add missing nodes to mapping
        for node_id in missing_ids:
            idx_map[node_id] = len(idx_map)

        # Map source and target IDs to indices
        edges["source_idx"] = edges["source_id"].map(idx_map)
        edges["target_idx"] = edges["target_id"].map(idx_map)

        # Ensure integer types
        edges["source_idx"] = edges["source_idx"].astype(int)
        edges["target_idx"] = edges["target_idx"].astype(int)

        return nodes, edges.reset_index(drop=True)

    except Exception as e:
        st.error(f"Error preprocessing graph: {e}")
        return None, None


def export_graph_data(plot_graph):
    """Export graph data with proper formatting"""
    try:
        # Handle node attributes
        node_data = {
            "id": plot_graph.vs["id"],
            "label": plot_graph.vs["label"],
            "type": plot_graph.vs["type"],
            "legislation_title": plot_graph.vs["legislation_title"],
        }

        # Add optional node attributes if they exist
        optional_attrs = [
            "text",
            "extent",
            "number_of_provisions",
            "number",
            "size",
            "colour",
            "shape",
        ]
        for attr in optional_attrs:
            if attr in plot_graph.vs.attribute_names():
                node_data[attr] = plot_graph.vs[attr]

        nodes_df = pd.DataFrame(node_data)

        # Handle edge attributes
        edge_data = {
            "source_id": [plot_graph.vs[e.source]["id"] for e in plot_graph.es],
            "target_id": [plot_graph.vs[e.target]["id"] for e in plot_graph.es],
            "type": plot_graph.es["type"],
        }

        # Add optional edge attributes
        if "text" in plot_graph.es.attribute_names():
            edge_data["text"] = plot_graph.es["text"]
        if "size" in plot_graph.es.attribute_names():
            edge_data["size"] = plot_graph.es["size"]

        edges_df = pd.DataFrame(edge_data)

        return nodes_df, edges_df

    except Exception as e:
        st.error(f"Error exporting graph data: {e}")
        return None, None


def add_download_buttons(plot_graph):
    """Add download functionality with proper error handling"""
    try:
        nodes_df, edges_df = export_graph_data(plot_graph)
        if nodes_df is None or edges_df is None:
            return

        col1, col2 = st.columns(2)

        with col1:
            st.download_button(
                label="📥 Download Nodes CSV",
                data=nodes_df.to_csv(index=False).encode("utf-8"),
                file_name="nodes.csv",
                mime="text/csv",
                help="Download the nodes data as a CSV file",
            )
            st.caption(f"Contains {len(nodes_df)} nodes")

        with col2:
            st.download_button(
                label="📥 Download Edges CSV",
                data=edges_df.to_csv(index=False).encode("utf-8"),
                file_name="edges.csv",
                mime="text/csv",
                help="Download the edges data as a CSV file",
            )
            st.caption(f"Contains {len(edges_df)} edges")

    except Exception as e:
        st.error(f"Error adding download buttons: {e}")


def create_visualization_options():
    """Create visualization options in sidebar"""
    try:
        st.sidebar.header("Node and Edge Sizing")

        node_sizing = st.sidebar.selectbox(
            "Node Size By", ["Degree Centrality", "Betweenness Centrality", "Constant"]
        )

        edge_sizing = st.sidebar.selectbox(
            "Edge Size By", ["Edge Betweenness", "Constant"]
        )

        st.sidebar.header("Layout")
        layout_algorithm = st.sidebar.selectbox(
            "Layout Algorithm",
            ["3d", "spring", "kamada_kawai", "fruchterman_reingold", "lgl", "graphopt"],
        )

        return node_sizing, edge_sizing, layout_algorithm

    except Exception as e:
        st.error(f"Error creating visualization options: {e}")
        return None, None, None


def create_sidebar_filters(edges_all):
    """Create sidebar filters with error handling"""
    try:
        st.sidebar.header("Filter edges")
        edge_types = sorted(set(edges_all["type"]))
        selected_edge_types = st.sidebar.multiselect(
            "Select edge types",
            edge_types,
            default=[
                "commentary_M",
                "part_of",
                "freetext_reference",
                "commentary_P",
                "commentary_F",
            ],
        )

        st.sidebar.header("Graph Selection")
        method = st.sidebar.selectbox(
            "Select Graph Method",
            ["egonet", "nth_largest_community", "default", "giant_component"],
        )

        params = {"method": method}

        if method == "nth_largest_community":
            params["resolution"] = st.sidebar.slider(
                "Community Detection Resolution", 0.01, 1.0, 0.1
            )
        elif method == "egonet":
            if "nodes_all" in st.session_state:
                node_labels = sorted(
                    st.session_state.nodes_all["legislation_title"].unique()
                )
                params["ego_node_labels"] = st.sidebar.multiselect(
                    "Select Nodes for Ego Network",
                    node_labels,
                    default="Housing Act 2004",
                )
                params["n_hops"] = st.sidebar.number_input("Number of Hops", 1, 3, 1)

        return selected_edge_types, params

    except Exception as e:
        st.error(f"Error creating sidebar filters: {e}")
        return None, None


@st.cache_data(show_spinner=True)
def build_graph(nodes, edges):
    # Create edge list using the correct indices
    edge_list = list(zip(edges["source_idx"], edges["target_idx"]))

    # Create the graph
    g = Graph(n=len(nodes), edges=edge_list, directed=True)

    # Add node attributes
    for col in nodes.columns:
        g.vs[col] = nodes[col].tolist()

    # Add edge attributes
    edge_attrs = edges.columns.difference(
        ["source_id", "source_idx", "target_id", "target_idx"]
    )
    for attr in edge_attrs:
        g.es[attr] = edges[attr].tolist()

    # Verify graph integrity
    assert g.vcount() >= len(nodes), "Number of vertices doesn't match"
    assert g.ecount() == len(edges), "Number of edges doesn't match"

    return g


@st.cache_data(show_spinner=True)
def select_graph(
    g, method="default", n=1, ego_node_labels=None, n_hops=1, resolution=0.1
):
    """
    Select and generate a graph based on different methods.
    """
    valid_methods = [
        "default",
        "giant_component",
        "nth_largest_component",
        "nth_largest_community",
        "egonet",
    ]

    # Parameter validation
    if method not in valid_methods:
        raise ValueError(f"Invalid method. Choose from {valid_methods}")

    if n <= 0:
        raise ValueError("Parameter 'n' must be greater than 0")

    if resolution <= 0:
        raise ValueError("Resolution must be greater than 0")

    if method == "egonet":
        if not ego_node_labels:
            raise ValueError("ego_node_labels must not be empty for egonet method")
        if n_hops <= 0:
            raise ValueError("n_hops must be greater than 0")

    # Functionality
    if method == "default":
        return g

    if method == "giant_component":
        components = g.components()
        return components.giant()

    if method == "nth_largest_component":
        components = g.components()
        component_sizes = [len(c) for c in components]
        if n > len(component_sizes):
            return g.subgraph([])  # Return empty graph if n is too large
        n_largest_component_idx = sorted(
            range(len(component_sizes)), key=lambda k: component_sizes[k], reverse=True
        )[n - 1]
        return components.subgraph(n_largest_component_idx)

    if method == "nth_largest_community":
        undirected_g = g.as_undirected()
        communities = undirected_g.community_leiden(resolution=resolution)
        community_sizes = communities.sizes()
        if n > len(community_sizes):
            return g.subgraph([])  # Return empty graph if n is too large
        n_largest_community_idx = sorted(
            range(len(community_sizes)), key=lambda k: community_sizes[k], reverse=True
        )[n - 1]
        return communities.subgraph(n_largest_community_idx)

    if method == "egonet":
        node_indices = []
        for node_label in ego_node_labels:
            matching_vertices = [
                v.index for v in g.vs if v["legislation_title"] == node_label
            ]
            for node_idx in matching_vertices:
                # Get all vertices within n_hops of the current vertex
                neighbours = g.neighborhood(node_idx, order=n_hops, mode="all")
                node_indices.extend(neighbours)

        # Remove duplicates and create subgraph
        node_indices = list(set(node_indices))
        if not node_indices:  # If no nodes were found
            st.warning(
                f"No nodes found matching the selected legislation titles: {ego_node_labels}"
            )
            return g.subgraph([])  # Return empty graph

        return g.subgraph(node_indices)


def simplify_large_graph(graph, max_nodes=1000):
    """Simplify large graphs before layout to reduce computation.
    Generates a subgraph of the top 1000 nodes based on their degree centrality."""
    if graph.vcount() > max_nodes:
        # Keep only the most important nodes
        degrees = graph.degree()
        top_nodes = sorted(range(len(degrees)), key=lambda x: degrees[x], reverse=True)[
            :max_nodes
        ]
        return graph.subgraph(top_nodes)
    return graph


@st.cache_data
def calculate_layout(plot_graph, layout_algorithm, seed=42):
    """Cache layout calculations for a given graph and algorithm"""

    # Set random seed for reproducible layouts
    random.seed(seed)

    if layout_algorithm == "spring":
        layout = plot_graph.layout_reingold_tilford_circular()
    elif layout_algorithm == "kamada_kawai":
        layout = plot_graph.layout_kamada_kawai(maxiter=100)  # Limit iterations
    elif layout_algorithm == "fruchterman_reingold":
        layout = plot_graph.layout_fruchterman_reingold(
            niter=50,  # Reduce iterations
        )
    elif layout_algorithm == "lgl":
        layout = plot_graph.layout_lgl(maxiter=100)  # Limit iterations
    elif layout_algorithm == "graphopt":
        layout = plot_graph.layout_graphopt(
            niter=100,  # Reduce iterations
            node_charge=0.02,  # Adjust repulsion
        )
    elif layout_algorithm == "3d":
        layout = plot_graph.layout_fruchterman_reingold_3d(
            niter=50,  # Reduce iterations
        )
    elif layout_algorithm == "kk_3d":
        layout = plot_graph.layout_kamada_kawai_3d(maxiter=100)  # Limit iterations
    elif layout_algorithm == "circular_3d":
        layout = plot_graph.layout_sphere()
    else:
        layout = plot_graph.layout_circle()  # Fallback to simple layout

    # Convert layout to list of tuples for caching
    return [tuple(coord) for coord in layout.coords]


@st.cache_data
def normalize_node_sizes(values, min_size=10, max_size=50, method="minmax"):
    """
    Normalize node sizes using different methods.

    Parameters:
    values (list): List of node values to normalize
    min_size (float): Minimum node size in the output
    max_size (float): Maximum node size in the output
    method (str): Normalization method ('minmax', 'log', 'sqrt')

    Returns:
    list: Normalized node sizes
    """
    if not values:
        return values

    values = np.array(values)

    if method == "minmax":
        # Simple min-max normalization
        min_val = np.min(values)
        max_val = np.max(values)
        if max_val == min_val:
            return [min_size] * len(values)
        normalized = (values - min_val) / (max_val - min_val)

    elif method == "log":
        # Logarithmic normalization (good for values with large ranges)
        min_val = np.min(values)
        # Shift values to ensure all are positive
        shifted = values - min_val + 1
        normalized = np.log(shifted)
        normalized = (normalized - np.min(normalized)) / (
            np.max(normalized) - np.min(normalized)
        )

    elif method == "sqrt":
        # Square root normalization (moderate scaling for large values)
        min_val = np.min(values)
        # Shift values to ensure all are positive
        shifted = values - min_val
        normalized = np.sqrt(shifted)
        normalized = normalized / np.max(normalized)

    else:
        raise ValueError(f"Unknown normalization method: {method}")

    # Scale to desired size range
    sizes = min_size + normalized * (max_size - min_size)
    return sizes.tolist()


def add_node_styling(plot_graph):
    colour_palette = matplotlib.colormaps.get_cmap("tab20")

    # Colour nodes by legislation_title
    unique_titles = list(set(plot_graph.vs["legislation_title"]))
    colour_palette = [
        "#" + "".join(random.choices("0123456789ABCDEF", k=6)) for _ in unique_titles
    ]
    title_colour_map = dict(zip(unique_titles, colour_palette))

    # Count the occurrences of each legislation title
    title_counts = pd.Series(plot_graph.vs["legislation_title"]).value_counts()

    # Create a dataframe for colour mapping
    colour_mapping_df = pd.DataFrame(
        {
            "Legislation Title": list(title_colour_map.keys()),
            "Colour": title_colour_map.values(),
        }
    )

    # Add the counts to the dataframe
    colour_mapping_df["Count"] = colour_mapping_df["Legislation Title"].map(
        title_counts
    )

    # Sort the dataframe by the count in descending order
    colour_mapping_df = colour_mapping_df.sort_values(
        by="Count", ascending=False
    ).reset_index(drop=True)

    # Assign shape to nodes depending on type
    node_shape_map_type = {
        "legislation": "square",
        "section": "circle",
        "schedule": "diamond",
    }

    def colour_mapping_style(val):
        return f"background-color: {val}"

    with st.expander("Legend"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Colour Mapping")
            st.dataframe(
                colour_mapping_df.style.map(colour_mapping_style, subset=["Colour"]),
                height=300,
            )

        with col2:
            st.subheader("Shape Mapping")
            shape_mapping_df = pd.DataFrame(
                list(node_shape_map_type.items()), columns=["Type", "Shape"]
            )
            st.dataframe(shape_mapping_df, height=300)

    node_colours = [title_colour_map[v["legislation_title"]] for v in plot_graph.vs]

    plot_graph.vs["colour"] = node_colours
    plot_graph.vs["shape"] = [
        node_shape_map_type[type] for type in plot_graph.vs["type"]
    ]

    return plot_graph


def create_graph_visualization(
    plot_graph, layout_coords, layout_algorithm, node_sizing, edge_sizing
):
    """Create the graph visualization using plotly"""
    # Apply node sizing
    if node_sizing == "Eigenvector Centrality":
        values = plot_graph.eigenvector_centrality()
        plot_graph.vs["size"] = normalize_node_sizes(values, method="minmax")
    elif node_sizing == "Degree Centrality":
        values = plot_graph.degree()
        plot_graph.vs["size"] = normalize_node_sizes(values, method="sqrt")
    elif node_sizing == "Betweenness Centrality":
        values = plot_graph.betweenness()
        plot_graph.vs["size"] = normalize_node_sizes(values, method="log")
    else:
        plot_graph.vs["size"] = [1] * plot_graph.vcount()

    # Apply edge sizing
    if edge_sizing == "Edge Betweenness":
        plot_graph.es["size"] = plot_graph.edge_betweenness()
    else:
        plot_graph.es["size"] = [1] * plot_graph.ecount()

    # Add styling to nodes
    plot_graph = add_node_styling(plot_graph)

    # Create hover text
    hover_text = [
        f"ID: {v['id']}<br>"
        f"Legislation: {v['legislation_title']}<br>"
        f"Type: {v['type']}<br>"
        f"Label: {v['label']}<br>"
        f"Extent: {'N/A' if 'extent' not in v.attributes() else v['extent']}<br>"
        f"Text: {'' if 'text' not in v.attributes() else str(v['text'])[:100]}...<br>"
        for v in plot_graph.vs
    ]

    # Create node labels - only show for legislation type nodes
    node_labels = []
    for v in plot_graph.vs:
        if v["type"] == "legislation" and v["legislation_title"]:
            node_labels.append(v["legislation_title"][:30])  # Truncate long titles
        else:
            node_labels.append("")  # Empty string for non-legislation nodes

    # Create traces based on layout algorithm
    if layout_algorithm in ["3d", "circular_3d", "kk_3d"]:
        x, y, z = zip(*layout_coords)
        node_trace = go.Scatter3d(
            x=x,
            y=y,
            z=z,
            mode="markers+text",
            marker=dict(
                size=[v["size"] for v in plot_graph.vs],
                color=[v["colour"] for v in plot_graph.vs],
                line=dict(width=2),
                sizemin=20,
                symbol=[v["shape"] for v in plot_graph.vs],
            ),
            text=node_labels,  # Use filtered labels here
            textposition="top center",
            hoverinfo="text",
            hovertext=hover_text,
            hoverlabel=dict(
                bgcolor=[v["colour"] for v in plot_graph.vs],
                font=dict(color="black"),
            ),
        )

        edge_trace = [
            go.Scatter3d(
                x=[x[e.source], x[e.target], None],
                y=[y[e.source], y[e.target], None],
                z=[z[e.source], z[e.target], None],
                mode="lines",
                line=dict(width=1, color="black"),
                hoverinfo="text",
                hovertext=f"Source: {plot_graph.vs[e.source]['id']}<br>Target: {plot_graph.vs[e.target]['id']}<br>Type: {e['type']}",
            )
            for e in plot_graph.es
        ]
    else:
        x, y = zip(*layout_coords)
        node_trace = go.Scatter(
            x=x,
            y=y,
            mode="markers+text",
            marker=dict(
                size=[v["size"] for v in plot_graph.vs],
                color=[v["colour"] for v in plot_graph.vs],
                line=dict(width=2),
                symbol=[v["shape"] for v in plot_graph.vs],
            ),
            text=node_labels,  # Use filtered labels here
            textposition="top center",
            textfont=dict(
                size=[14 if v["type"] == "legislation" else 0 for v in plot_graph.vs],
                color="black",
            ),
            hoverinfo="text",
            hovertext=hover_text,
            hoverlabel=dict(
                bgcolor=[v["colour"] for v in plot_graph.vs],
                font=dict(color="black"),
            ),
        )

        edge_trace = [
            go.Scatter(
                x=[x[e.source], x[e.target], None],
                y=[y[e.source], y[e.target], None],
                mode="lines",
                line=dict(width=e["size"], color="black"),
                hoverinfo="text",
                hovertext=f"Source: {plot_graph.vs[e.source]['id']}<br>Target: {plot_graph.vs[e.target]['id']}<br>Type: {e['type']}",
            )
            for e in plot_graph.es
        ]

    # Create and return figure
    fig = go.Figure(
        data=edge_trace + [node_trace],
        layout=go.Layout(
            showlegend=False,
            hovermode="closest",
            margin=dict(b=0, l=0, r=0, t=0),
            xaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False, visible=False
            ),
            yaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False, visible=False
            ),
            height=900,
        ),
    )

    fig.update_layout(dragmode="pan")

    return fig


def process_and_display_graph(
    selected_edge_types, method_params, node_sizing, edge_sizing, layout_algorithm
):
    """Helper function to process and display the graph"""
    try:
        # Filter edges
        filtered_edges = st.session_state.edges_all[
            st.session_state.edges_all["type"].isin(selected_edge_types)
        ]

        # Build and process graph
        g = build_graph(st.session_state.nodes_all, filtered_edges)
        plot_graph = select_graph(g, **method_params)
        plot_graph = simplify_large_graph(plot_graph)

        # Calculate layout
        layout_coords = calculate_layout(plot_graph, layout_algorithm)

        # Store current state
        st.session_state.current_graph = plot_graph
        st.session_state.current_layout = layout_coords

        # Create and store visualization
        st.session_state.current_fig = create_graph_visualization(
            plot_graph, layout_coords, layout_algorithm, node_sizing, edge_sizing
        )

    except Exception as e:
        st.error(f"Error processing graph: {e}")


def main():
    """Main application function"""
    try:
        st.title("UK Legislation Graph Explorer")

        # Load data
        nodes_all, edges_all = load_data()
        if nodes_all is None or edges_all is None:
            st.error("Failed to load data. Please check your data files.")
            return

        # Initialize session state
        if "nodes_all" not in st.session_state or "edges_all" not in st.session_state:
            nodes_all, edges_all = preprocess_graph(nodes_all, edges_all)
            if nodes_all is None or edges_all is None:
                return
            st.session_state.nodes_all = nodes_all
            st.session_state.edges_all = edges_all

        # Create filters and options
        selected_edge_types, method_params = create_sidebar_filters(
            st.session_state.edges_all
        )
        node_sizing, edge_sizing, layout_algorithm = create_visualization_options()

        # Initially process graph if no current graph exists
        if "current_graph" not in st.session_state:
            process_and_display_graph(
                selected_edge_types,
                method_params,
                node_sizing,
                edge_sizing,
                layout_algorithm,
            )

        # Add an Update Visualization button to the sidebar
        if st.sidebar.button("Update Visualization", type="primary"):
            # Clear previous download data when updating visualization
            if "download_data" in st.session_state:
                del st.session_state.download_data

            # Update the visualization
            process_and_display_graph(
                selected_edge_types,
                method_params,
                node_sizing,
                edge_sizing,
                layout_algorithm,
            )

        # Create columns for download buttons and metrics
        col1, col2 = st.columns([2, 1])

        # If we have a current graph, display everything
        if "current_graph" in st.session_state and "current_fig" in st.session_state:
            # Display the main visualization
            st.plotly_chart(st.session_state.current_fig, use_container_width=True)

            with col1:
                # Display metrics
                st.divider()
                with st.expander("Graph Metrics"):
                    display_graph_metrics(st.session_state.current_graph)

            with col2:
                # Display configuration details
                st.divider()
                with st.expander("Graph Configuration Details"):
                    st.write("**Current Settings:**")
                    st.json(
                        {
                            "Layout Algorithm": layout_algorithm,
                            "Node Sizing": node_sizing,
                            "Edge Sizing": edge_sizing,
                            "Selected Edge Types": selected_edge_types,
                            "Graph Method": method_params["method"],
                            **{k: v for k, v in method_params.items() if k != "method"},
                        }
                    )
            # Add download section
            st.divider()
            add_download_buttons(st.session_state.current_graph)

    except Exception as e:
        st.error(f"An error occurred in the main application: {e.__traceback__}")
        st.error("Please refresh the page and try again.")
        print(e)
        print(e.with_traceback(e.__traceback__))


if __name__ == "__main__":
    main()
