from abc import ABC, abstractmethod
from typing import Dict

from kg.scraper.dota.types import DotaItem


class BaseScraper(ABC):
    NAME: str = "base_scraper"

    @abstractmethod
    def scrape(self) -> Dict[str, DotaItem]:
        pass
