import argparse
import logging
from pathlib import Path

from kg.logger import getLogger, setLevel
from kg.onto.builder import DotaOntoBuilder
from kg.scraper.dota.utils import parse_from_json

logger = getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate KG-Dota RDF ontology from item JSON."
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input JSON file. If not given, just builds the base of the ontology.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default="kg-dota.rdf",
        help="Path to output RDF file (default: kg-dota.rdf)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
        default=False,
    )
    args = parser.parse_args()

    # Configure logger
    setLevel(logging.DEBUG if args.verbose else logging.INFO)

    # Load and process data
    in_path = str(args.input) if args.input else None

    onto_builder = DotaOntoBuilder()
    logger.info("building schema...")
    onto_builder.build_schema()

    if in_path:
        logger.info(f"Loading items from {args.input}")
        data = parse_from_json(str(args.input))
        onto_builder.build(data)

    # Serialize
    logger.info(f"Writing RDF to {args.output}")
    onto_builder.save_to_file(str(args.output))


if __name__ == "__main__":
    main()
