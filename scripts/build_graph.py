import argparse
import json
import os
import re
from pathlib import Path
from time import perf_counter
from typing import List, Optional

import dotenv
import yaml

from lex_graph.graph import LegislationGraph
from lex_graph.types import Legislation

dotenv.load_dotenv()


def get_processed_files(
    input_path: Path,
    year: Optional[int] = None,
    type: Optional[str] = None,
    chapter: Optional[int] = None,
) -> List[Path]:
    """Get files matching the specified criteria."""
    if year is not None:
        base_path = input_path / str(year)
    else:
        base_path = input_path

    if not base_path.exists():
        raise ValueError(f"Path does not exist: {base_path}")

    all_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith("-revised-data.json"):
                all_files.append(Path(root) / file)

    if year is not None and type is not None and chapter is not None:
        pattern = re.compile(
            rf"{type}-{year}-{chapter}-revised-data\.json$|{type}-Geo\d+-\d+-\d+-revised-data\.json$"
        )
        all_files = [f for f in all_files if pattern.match(f.name)]
    elif year is not None and chapter is not None:
        pattern = re.compile(
            rf".*-{year}-{chapter}-revised-data\.json$|.*-Geo\d+-\d+-\d+-revised-data\.json$"
        )
        all_files = [f for f in all_files if pattern.match(f.name)]
    elif year is not None and type is not None:
        pattern = re.compile(
            rf"{type}-{year}-\d+-revised-data\.json$|{type}-Geo\d+-\d+-\d+-revised-data\.json$"
        )
        all_files = [f for f in all_files if pattern.match(f.name)]
    elif year is not None:
        pattern = re.compile(
            rf".*-{year}-\d+-revised-data\.json$|.*-Geo\d+-\d+-\d+-revised-data\.json$"
        )
        all_files = [f for f in all_files if pattern.match(f.name)]
    elif type is not None:
        pattern = re.compile(
            rf"{type}-\d+-\d+-revised-data\.json$|{type}-Geo\d+-\d+-\d+-revised-data\.json$"
        )
        all_files = [f for f in all_files if pattern.match(f.name)]

    return all_files


def load_yaml_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Process legislation XML files.")

    # Add config file option
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file",
    )

    # Input/output paths
    parser.add_argument(
        "--input_path",
        default="data/processed",
        help="Path to input directory (default: data/processed)",
    )
    parser.add_argument(
        "--output_path",
        default="data/graph",
        help="Path to output directory (default: data/graph)",
    )

    # Processing mode group
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Test processing a single file",
    )
    mode_group.add_argument("--file", default=None, help="Process a single file")
    mode_group.add_argument(
        "--all", action="store_true", default=False, help="Process all files"
    )
    mode_group.add_argument(
        "--year", type=int, default=None, help="Process files from specific year"
    )

    # Optional additional type filter
    parser.add_argument(
        "--type",
        default=None,
        help="Filter by legislation type (e.g., ukpga, eudn, asp)",
    )

    # Build arguments
    parser.add_argument(
        "--granularity", default="section", help="Graph granularity (default: section)"
    )

    args = parser.parse_args()

    # If config file is provided, load it and merge with command line args
    if args.config:
        config = load_yaml_config(args.config)
        # Get all default values from argparse
        defaults = {
            action.dest: parser.get_default(action.dest)
            for action in parser._actions
            if action.dest != "help"
        }
        # Update defaults with config values
        defaults.update(config)
        # Update with any command-line arguments that were explicitly set
        args_dict = vars(args)
        for key, value in args_dict.items():
            if value != parser.get_default(key) and key != "config":
                defaults[key] = value
        return argparse.Namespace(**defaults)

    # Validate that either config or required args are provided
    if not any([args.file, args.all, args.test, args.year]):
        parser.error(
            "Either --config or one of --file, --all, --test, or --year is required"
        )

    return args


def main():
    args = parse_arguments()

    input_path = Path(args.input_path)

    if args.file:
        print(f"Processing single file: {args.file}")
        files = [Path(args.file)]
    elif args.test:
        files = [Path("./data/processed/2004/ukpga-2004-34-revised-data.json")]
    elif args.all and args.type:
        print(f"Processing all files of type: {args.type}")
        files = get_processed_files(input_path, type=args.type)
    else:
        print(f"Processing files from {input_path}")
        files = get_processed_files(input_path, args.year, args.type)

    if len(files) == 0:
        raise ValueError("No files found to process")

    print(f"Found {len(files)} files, loading files...")
    load_time = perf_counter()
    legislations = []
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            legislation = Legislation.model_validate(data)
            legislations.append(legislation)
    print(
        f"Loaded {len(legislations)} files in {(perf_counter() - load_time) / 60:.2f} minutes"
    )

    print("Building graph...")
    build_time = perf_counter()
    graph = LegislationGraph.from_legislations(
        legislations, granularity=args.granularity
    )
    graph.print_summary()
    graph.save(args.output_path + "/graph")
    graph.save_edgelist(args.output_path + "/edgelist")
    graph.save_neo4j(args.output_path + "/neo4j")
    print(f"Built graph in {(perf_counter() - build_time) / 60:.2f} minutes")


if __name__ == "__main__":
    main()
