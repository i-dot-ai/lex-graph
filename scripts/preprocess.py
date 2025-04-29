#!/usr/bin/env python3
import argparse
import json
import os
import re
import traceback
from multiprocessing import Pool, cpu_count
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, List, Optional

import dotenv
import yaml
from tqdm import tqdm

from lex_graph.exceptions import LegislationParsingError
from lex_graph.parsers.parser import LegislationParser
from lex_graph.types import Legislation

dotenv.load_dotenv()


class LegislationProcessor:
    def __init__(self, input_path: str = "data/raw", output_path: str = "data/output"):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.parser = LegislationParser()

    def get_files(
        self,
        year: Optional[int] = None,
        type: Optional[str] = None,
        chapter: Optional[int] = None,
    ) -> List[Path]:
        """Get files matching the specified criteria."""
        if year is not None:
            base_path = self.input_path / str(year)
        else:
            base_path = self.input_path

        if not base_path.exists():
            raise ValueError(f"Path does not exist: {base_path}")

        all_files = []
        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith("-revised-data.xml"):
                    all_files.append(Path(root) / file)

        if year is not None and type is not None and chapter is not None:
            pattern = re.compile(
                rf"{type}-{year}-{chapter}-revised-data\.xml$|{type}-Geo\d+-\d+-\d+-revised-data\.xml$"
            )
            all_files = [f for f in all_files if pattern.match(f.name)]
        elif year is not None and chapter is not None:
            pattern = re.compile(
                rf".*-{year}-{chapter}-revised-data\.xml$|.*-Geo\d+-\d+-\d+-revised-data\.xml$"
            )
            all_files = [f for f in all_files if pattern.match(f.name)]
        elif year is not None and type is not None:
            pattern = re.compile(
                rf"{type}-{year}-\d+-revised-data\.xml$|{type}-Geo\d+-\d+-\d+-revised-data\.xml$"
            )
            all_files = [f for f in all_files if pattern.match(f.name)]
        elif year is not None:
            pattern = re.compile(
                rf".*-{year}-\d+-revised-data\.xml$|.*-Geo\d+-\d+-\d+-revised-data\.xml$"
            )
            all_files = [f for f in all_files if pattern.match(f.name)]
        elif type is not None:
            pattern = re.compile(
                rf"{type}-\d+-\d+-revised-data\.xml$|{type}-Geo\d+-\d+-\d+-revised-data\.xml$"
            )
            all_files = [f for f in all_files if pattern.match(f.name)]
        return all_files

    def process_file(self, file_path: Path) -> Legislation:
        """Process a single legislation file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                xml_content = f.read()

            legislation = self.parser.parse(xml_content)

            # Create output directory if it doesn't exist
            output_dir = self.output_path / str(file_path.parent.name)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Save processed data
            output_file = output_dir / f"{file_path.stem}.json"
            self._save_legislation(legislation, output_file)

            return legislation

        except Exception as e:
            traceback_str = "".join(traceback.format_tb(e.__traceback__))
            raise LegislationParsingError(
                f"Error processing {file_path}: {str(e)}\nStack trace:\n{traceback_str}"
            )

    def process_multiple_files(self, files: List[Path]) -> List:
        """Process multiple legislation files using multiprocessing."""

        processed_legislations = []

        start_time = perf_counter()

        with Pool(processes=cpu_count()) as pool:
            for result in tqdm(
                pool.imap_unordered(self._process_file_wrapper, files),
                total=len(files),
                desc="Processing files",
            ):
                if result:
                    processed_legislations.append(result)

        end_time = perf_counter()
        print(
            f"Processing completed in {end_time - start_time:.2f} seconds. Average time per file: {(end_time - start_time) / len(files):.2f} seconds"
        )
        print(f"Successfully processed {len(processed_legislations)} files")

        return processed_legislations

    def _process_file_wrapper(self, file_path: Path) -> Optional[Legislation]:
        """Wrapper for processing a file to be used with multiprocessing."""
        try:
            return self.process_file(file_path)
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None

    def _save_legislation(self, legislation, output_file: Path) -> None:
        """Save processed legislation to output file."""
        with open(output_file, "w", encoding="utf-8") as f:
            json_data = json.loads(legislation.model_dump_json())
            json.dump(json_data, f, indent=4, ensure_ascii=False, sort_keys=True)


def load_yaml_config(config_path: str) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def parse_arguments():
    parser = argparse.ArgumentParser(description="Process legislation XML files.")

    # Config file option as input instead of command line arguments
    parser.add_argument(
        "--config",
        help="Path to YAML configuration file",
    )

    # Input/output paths
    parser.add_argument(
        "--input_path",
        default="data/raw",
        help="Path to input directory (default: data/raw)",
    )
    parser.add_argument(
        "--output_path",
        default="data/processed",
        help="Path to output directory (default: data/processed)",
    )

    # Processing mode group
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--file", default=None, help="Process a single file")
    mode_group.add_argument(
        "--all", action="store_true", default=False, help="Process all files"
    )
    mode_group.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Test processing a single file",
    )
    mode_group.add_argument(
        "--year", type=int, default=None, help="Process files from specific year"
    )

    # Additional filters
    parser.add_argument(
        "--type",
        default=None,
        help="Filter by legislation type (e.g., ukpga, eudn, asp)",
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

    # Initialize processor
    processor = LegislationProcessor(args.input_path, args.output_path)

    try:
        if args.file:
            # Process single file
            file_path = Path(args.file)
            legislation = processor.process_file(file_path)
            if legislation:
                print(f"Successfully processed: {file_path}")

        elif args.all:
            # Process all files
            if args.type:
                files = processor.get_files(type=args.type)
            else:
                files = processor.get_files()
            processor.process_multiple_files(files)

        elif args.year or args.type:
            # Process files from specific year with optional type filter
            files = processor.get_files(args.year, args.type)
            if not files:
                print(
                    f"No matching files found for year {args.year}"
                    f"{f' and type {args.type}' if args.type else ''}"
                )
                return

            print(f"Found {len(files)} matching files")
            processor.process_multiple_files(files)

        elif args.test:
            # Test processing a single file
            file_path = Path("./data/raw/2004/ukpga-2004-34-revised-data.xml")
            legislation = processor.process_file(file_path)
            if legislation:
                print(
                    f"Successfully processed: {file_path} | Num Sections: {len(legislation.sections)} | Num Schedules: {len(legislation.schedules)} | Num Commentaries: {len(legislation.commentaries)} | Num Commentary Refs: {len(legislation.all_commentary_refs())} | Num Text References: {len(legislation.all_references())}"
                )

    except Exception as e:
        print(f"Error: {str(e)}")
        return 1

    return 0


if __name__ == "__main__":
    main()
