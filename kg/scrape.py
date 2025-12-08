import argparse
import logging
from typing import Dict

from kg.logger import getLogger, setLevel
from kg.scraper.dota.utils import (
    get_recipes_count,
    parse_from_json,
    remove_distinct_recipes,
    save_to_json,
    set_distinct_recipes,
    set_orders,
)
from kg.scraper.scrapers.base_scraper import BaseScraper
from kg.scraper.scrapers.dota2_ru_scraper import Dota2RuScraper
from kg.scraper.scrapers.fandom_scraper import FandomScraper

SCRAPERS: Dict[str, type[BaseScraper]] = {
    "dota2_ru": Dota2RuScraper,
    "fandom": FandomScraper,
}


def main(
    input_file: str,
    output_file: str,
    scraper_name: str,
    assign_orders: bool = True,
    distinct_recipes: bool = False,
    verbose: bool = False,
) -> None:
    # configure logger
    logger = getLogger(__name__)
    setLevel(logging.DEBUG if verbose else logging.INFO)

    if scraper_name not in SCRAPERS:
        raise ValueError(f"Unknown scraper: {scraper_name}")
    if scraper_name == "fandom":
        logger.warning("Fandom scraper may be outdated/broken")
    scraper = SCRAPERS[scraper_name]()
    logger.debug(f"using scraper {scraper.NAME}")

    if input_file:
        logger.debug(f"reading from input file: {input_file}")
        res = parse_from_json(input_file)
        recipe_count = get_recipes_count(res)
        logger.debug(
            f"loaded {len(res) - recipe_count} items from {input_file} (+{recipe_count} recipes)."
        )
    else:
        logger.info("scraping data from the site...")
        res = scraper.scrape()
        logger.info(f"Scraped {len(res.values())} items.")
    if assign_orders:
        logger.info("assigning orders to items...")
        res = set_orders(res)  # assign orders
    if distinct_recipes:
        logger.info("using distinct recipes for items...")
        res = set_distinct_recipes(res)
    else:
        logger.info("using default recipes for items...")
        res = remove_distinct_recipes(res)

    save_to_json(output_file, res)
    logger.info(f"data saved to {output_file}.")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape Dota 2 items and save them to a JSON file."
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
        default=False,
    )

    parser.add_argument(
        "--input",
        type=str,
        help="Input file to load data from (optional, used to assign orders only)",
    )

    parser.add_argument(
        "--output",
        type=str,
        help="Output file to save the scraped data.",
        default="items.json",
    )

    parser.add_argument(
        "--scraper",
        type=str,
        choices=list(SCRAPERS.keys()),
        default="dota2_ru",
        help="Specify which scraper to use.",
    )

    parser.add_argument(
        "--no-assign-orders",
        action="store_false",
        default=True,
        help="Whether to assign orders to items (default: True)",
    )

    parser.add_argument(
        "--no-distinct-recipes",
        action="store_false",
        default=True,
        help="""Whether to use distinct recipes (default: True).
        By default items that require a recipe will have just 'Recipe' in their recipe list.
        With this flag, recipes will be named uniquely per item, e.g. \"Wind Waker Recipe\"""",
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    main(
        args.input,
        args.output,
        args.scraper,
        args.no_assign_orders,
        args.no_distinct_recipes,
        args.verbose,
    )
