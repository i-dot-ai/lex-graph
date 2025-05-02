# Lex Graph 🕸️
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)
![Maturity level-Prototype](https://img.shields.io/badge/Maturity%20Level-Prototype-red)

This repo builds a knowledge graph from UK legislation and provides an application for exploring the graph.

Originally prototyped by [@livadlivesey](https://github.com/livadlivesey) and [@GavEdwards](https://github.com/GavEdwards). 

![Header Image](header.jpg)

## Accessing the Graph ⬇️📄

This repo is the code used to build Lex Graph from scratch. If you wish to simply access the produced knowledge graph, Lex Graph can be downloaded from [i.AI's Hugging Face Datasets](https://huggingface.co/i-dot-ai).

## Setup 🛠️

To build the Lex Graph from scratch, please follow these steps: 

1. Clone the repo

```bash
git clone https://github.com/i-dot-ai/lex-graph-build.git
```

2. Install poetry if you don't have it

```bash
pip install poetry
```

3. Install the dependencies and create a virtual environment

```bash
poetry install
```


## Download raw legislation data 📥


A dump of the latest XML versions of legislation is available from the new Legislation Research website from the National Archives. At the time of publishing this is in beta. If you are interested in gaining access to the raw data to build the graph from scratch, please contact the Legislation Data Team (data.legislation@nationalarchives.gov.uk).

Once you have access, download the Legislative Texts Enacted CLML data and unzip it into [data/raw](data/raw).

![image](https://github.com/user-attachments/assets/e265f3b8-c5c2-4fea-a08b-e56514061513)


## Build the graph 🚀


The graph build process consists of two steps:
1. Pre-processing the raw data

2. Building the graph

The processed data is saved in the [data/processed](data/processed) directory and the graph is saved in the [data/graph](data/graph) directory.

### Processing raw data

Process a single test file

```bash
poetry run python scripts/preprocess.py --test
```

Process a custom file

```bash
poetry run python scripts/preprocess.py --file <file_path>
```

Process a subset of files

```bash
poetry run python scripts/preprocess.py --year <year> --type <type>
```

Process all files

```bash
poetry run python scripts/preprocess.py --all
```

Use a different input path (default input is `data/raw`, default output is `data/processed`)

```bash
poetry run python scripts/preprocess.py --input_path <input_path> --output_path <output_path>
```

You can also use a yaml configuration file instead of, or alongside, the command line arguments
```bash
poetry run python scripts/preprocess.py --config configs/preprocess_config.yaml
```

### Building the graph

Build graph from a single test file

```bash
poetry run python scripts/build_graph.py --test
```

Build graph from a custom file

```bash
poetry run python scripts/build_graph.py --file <file_path>
```

Build graph from a subset of files

```bash
poetry run python scripts/build_graph.py --year <year> --type <type>
```

Build graph from all files

```bash
poetry run python scripts/build_graph.py --all
```

You can also use a yaml configuration file instead of, or alongside, the command line arguments
```bash
poetry run python scripts/build_graph.py --config configs/graph_config.yaml
```


## Streamlit App 🌐

The Streamlit app provides an interactive interface for exploring the UK legislation graph.
The Streamlit app in the [demo](demo) folder provides an interactive interface for exploring the UK legislation graph. The [app.py](demo/app.py) file in the [demo](demo) directory is the main entry point for the Streamlit application. It provides various functionalities for exploring and visualizing the legislation graph. See the README in the [demo](demo) folder for more details.


## Limitations

This is a prototype and does not guarantee accurate data. The codebase and features are subject to change. Some functionality may be experimental and require further testing and validation.

- **Data Coverage**: This prototype currently processes UK legislation data from the National Archives, but may not capture all legislative documents or their complete revision history. Some older or specialised documents might be missing or incompletely processed.
- **Graph Completeness**: The relationships between legislative documents are primarily based on explicit references found in the XML files. Implicit connections, contextual relationships, or references using non-standard formats may be missed.
- **Data Accuracy**: While we strive for accuracy, the automated parsing and graph construction process may contain errors, particularly when handling:
    - Complex nested legislative structures
    - Unusual formatting or non-standard XML structures
    - Cross-references using ambiguous or incomplete citations
    - Amendments and repeals that are conditionally applied

- **Performance Considerations**: Processing the complete legislative dataset can be computationally intensive and time-consuming. On a well-powered laptop (e.g., Apple M3 Macbook Pro), we have found it takes up to 30 minutes to preprocess the full set of XML files (~15 minutes) and build the graph (~15 minutes). Users working with the full dataset should ensure adequate system resources are available.

- **Visualisation Constraints** : The Streamlit visualization interface may experience performance limitations when displaying very large subgraphs or handling complex queries on the full dataset.

- **Legal Disclaimer**: This tool is intended for research and analysis purposes only. It should not be relied upon for legal advice or as an authoritative source of legislation. Users should always refer to official sources for current and accurate legislative information.


## Credits

This project builds upon and was inspired by the work of the Graphie team at King’s Quantitative and Digital Law Lab (QuantLaw), King's College London. Their original project Graphie demonstrated innovative approaches to legal knowledge graph construction and analysis of UK legislation, based on the Housing Act 2004. We encourage those interested in legal knowledge graphs to explore the original [Graphie](https://graphie.quantlaw.co.uk/) project available at: [https://github.com/kclquantlaw/graphie](https://github.com/kclquantlaw/graphie).

All data is sourced from [The National Archives legislation wesbite](https://www.legislation.gov.uk/). Crown © and database right material reused under the Open Government Licence v3.0. Material derived from the European Institutions © European Union, 1998-2019, reused under the terms of Commission Decision 2011/833/EU.
