from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional

from kg.scraper.dota.types import DotaItem, NeutralItem


@dataclass
class ScrapeResult:
    dota_items: Optional[Dict[str, DotaItem]] = None
    neutral_items: Optional[Dict[str, NeutralItem]] = None


class BaseScraper(ABC):
    NAME: str = "base_scraper"

    @abstractmethod
    def scrape(self) -> ScrapeResult:
        pass
