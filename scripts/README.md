# Lex Graph Build Usage

The graph build consists of two steps:

1. Processing the raw data (`process.py`)
2. Building the graph (`build_graph.py`)

The processed data is saved in the [data/processed](data/processed) directory and the graph is saved in the [data/graph](data/graph) directory.

## Processing Raw Data

This script processes legislation XML files and converts them into JSON format.

**Classes**:

- `LegislationProcessor`: Handles the processing of legislation files, including reading, parsing, and saving the processed data.

**Functions**:

- `parse_arguments()`: Parses command-line arguments for the script.
- `main()`: Main function that initializes the processor and processes files based on the provided arguments.

**Usage**:
- `--input_path`: Path to the input directory containing XML files (default: `data/raw`).
- `--output_path`: Path to the output directory for saving processed JSON files (default: `data/processed`).
- `--file`: Process a single file specified by its path.
- `--all`: Process all files in the input directory.
- `--test`: Test processing a single file (default file path is used).
- `--year`: Process files from a specific year.
- `--type`: Filter files by legislation type (e.g., `ukpga`, `eudn`, `asp`).

Process a single test file:

```bash
poetry run python scripts/process.py --test
```

Process a custom file:

```bash
poetry run python scripts/process.py --file <file_path>
```

Process a subset of files:

```bash
poetry run python scripts/process.py --year <year> --type <type>
```

Process all files:

```bash
poetry run python scripts/process.py --all
```

Use a different input path (default input is `data/raw`, default output is `data/processed`):

```bash
poetry run python scripts/process.py --input_path <input_path> --output_path <output_path>
```

## Building the Graph

This script processes legislation XML files and builds a graph representation of the legislation.

**Functions**:

- `get_processed_files(input_path: Path, year: Optional[int] = None, type: Optional[str] = None, chapter: Optional[int] = None) -> List[Path]`: Get files matching the specified criteria.
- `parse_arguments()`: Parse command-line arguments.
- `main()`: Main function to process legislation files and build the graph.

**Usage**:
Run the script with appropriate command-line arguments to process legislation files and build a graph.

**Command-line Arguments**:
- `--input_path`: Path to input directory (default: `data/processed`).
- `--output_path`: Path to output directory (default: `data/graph`).
- `--test`: Test processing a single file.
- `--file`: Process a single file.
- `--all`: Process all files.
- `--year`: Process files from a specific year.
- `--type`: Filter by legislation type (e.g., `ukpga`, `eudn`, `asp`).
- `--granularity`: Graph granularity (default: `section`).

Build graph from a single test file:

```bash
poetry run python scripts/build_graph.py --test
```

Build graph from a custom file:

```bash
poetry run python scripts/build_graph.py --file <file_path>
```

Build graph from a subset of files:

```bash
poetry run python scripts/build_graph.py --year <year> --type <type>
```

Build graph from all files:

```bash
poetry run python scripts/build_graph.py --all
```
