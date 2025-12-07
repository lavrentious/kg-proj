import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import requests
from bs4 import BeautifulSoup, Tag

from scraper.dota.types import Buffs, DotaItem
from scraper.dota.utils import parse_buffs, raw_to_name_cost
from scraper.scrapers.base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class FandomScraper(BaseScraper):
    NAME: str = "fandom"
    items: Dict[str, DotaItem] = {}

    def __init__(self) -> None:
        pass

    def _build_dota_item(self, item: Tag) -> DotaItem | None:
        title = item.get("title")
        if not isinstance(title, str):
            logger.error(f"no title for {item.text}")
            return None
        data = raw_to_name_cost(title)
        if not data:
            logger.error(f"no data for {item.text}")
            return None
        name, cost = data
        if name in self.items:
            logger.debug(f"Already cached {name}")
            return self.items[name]

        img = item.find("img")
        img_url = None
        if img and isinstance(img, Tag):
            src = img.get("src")
            if not isinstance(src, str) or not src or src.startswith("data:"):
                src = img.get("data-src")
                if not isinstance(src, str) or not src or src.startswith("data:"):
                    logger.error(f"no src for {name}")
                    return None
            img_url = src

        if not img_url:
            logger.error(f"no img url for {name}")
            return None

        href = item.get("href")
        if href is None or not isinstance(href, str):
            logger.error(f"no href for {name}")
            return None
        item_url = "https://dota2.fandom.com" + href

        # item page scraper soup
        response = requests.get(item_url)
        soup = BeautifulSoup(response.text, "html.parser")

        recipe = self._scrape_item_recipe(soup, name)
        if recipe is None:
            logger.error(f"could not parse recipe for {name}")
            return None

        # scrape buffs
        buffs = self._scrape_buffs(soup, name)

        logger.debug(
            f"Name: {name}, Cost: {cost}, Image: {img_url}, URL: {item_url}, Recipe: {recipe}"
        )
        obj = DotaItem(
            name=name,
            cost=cost,
            image=img_url,
            url=item_url,
            recipe=recipe,
            buffs=buffs if buffs else Buffs(),
            order=None,
        )
        self.items[name] = obj
        return obj

    def _scrape_buffs(self, soup: BeautifulSoup, name: str) -> Buffs | None:
        logger.debug(f"scraping buffs for {name}")
        rows = soup.find_all("tr")
        td: Tag | None = None
        for row in rows:
            th = row.find("th")
            if not th or "bonus" not in th.text.lower():
                continue
            tds = row.find_all("td")
            td = tds[-1] if tds else None
        if not td:
            return None

        buffs = []
        current_bonus = ""

        for child in td.children:
            if isinstance(child, str):
                if child == "\n":
                    if current_bonus.strip():
                        buffs.append(current_bonus.strip())
                        current_bonus = ""
                else:
                    current_bonus += child
            elif hasattr(child, "name"):
                if child.name == "br":
                    if current_bonus.strip():
                        buffs.append(current_bonus.strip())
                        current_bonus = ""
                elif child.name == "a":
                    current_bonus += child.get_text()

        if current_bonus.strip():
            buffs.append(current_bonus.strip())

        if not buffs:
            return None
        logger.debug(f"buffs for {name}: {buffs}")
        return parse_buffs(buffs)

    def _scrape_item_recipe(self, soup: BeautifulSoup, name: str) -> List[str] | None:
        logger.debug(f"Fetching recipe for: {name}")

        info_table = soup.find("table", class_="infobox")
        if not info_table or not isinstance(info_table, Tag):
            logger.error("No infobox found")
            return None

        trs = info_table.find_all("tr")
        if not trs:
            logger.error("No table rows found")
            return None

        last_tr = trs[-1]
        if not isinstance(last_tr, Tag):
            logger.error("Last row is not a tag")
            return None

        th = last_tr.find("th")
        if not th or not isinstance(th, Tag):
            logger.error("No <th> found in last <tr>")
            return None

        children = [child for child in th.children if isinstance(child, Tag)]
        if not children:
            logger.error("No children found in <th>")
            return None

        last_child = children[-1]

        component_links = last_child.find_all("a")
        recipe_components = []
        for a in component_links:
            if not isinstance(a, Tag):
                logger.error("Component link is not a tag")
                continue
            title = a.get("title")
            href = a.get("href")
            if title and href and isinstance(title, str) and isinstance(href, str):
                data = raw_to_name_cost(title)
                if not data:
                    logger.error(f"no data for {title}")
                    continue
                if data[0] == name:
                    continue
                logger.debug(f"Component title: {title}, href: {href}, data: {data}")
                if data[0].lower() != "recipe" and data[0] not in self.items:
                    # fetch component item details if not cached
                    logger.debug(f"missing item in recipe: {data[0]}, fetching...")
                    self._build_dota_item(a)
                recipe_components.append(data[0])

        return recipe_components

    def scrape(self) -> Dict[str, DotaItem]:
        self.items.clear()
        response = requests.get("https://dota2.fandom.com/wiki/Items")
        soup = BeautifulSoup(response.text, "html.parser")

        target_sections = {"Basics Items", "Upgraded Items"}
        res_items: List[Tag] = []

        for h2 in soup.find_all("h2"):
            if not isinstance(h2, Tag):
                continue
            span = h2.find("span", class_="mw-headline")
            if not span or span.text.strip() not in target_sections:
                continue

            sibling = h2.find_next_sibling()
            while sibling:
                if isinstance(sibling, Tag) and sibling.name == "h2":
                    break

                if (
                    isinstance(sibling, Tag)
                    and sibling.name == "div"
                    and "itemlist" in sibling.get("class", [])  # type: ignore
                ):
                    items = sibling.find_all("div", recursive=False)
                    for item in items:
                        if not isinstance(item, Tag):
                            continue
                        a = item.find("a")
                        if a and isinstance(a, Tag):
                            res_items.append(a)

                sibling = sibling.find_next_sibling()

        with ThreadPoolExecutor(max_workers=12) as executor:
            future_to_tag = {
                executor.submit(self._build_dota_item, item): item for item in res_items
            }
            for future in as_completed(future_to_tag):
                item = future_to_tag[future]
                try:
                    result = future.result()
                    if result:
                        self.items[result.name] = result
                except Exception as exc:
                    logger.error(f"item {item} generated an exception: {exc}")

        logger.info(f"parsed: {len(self.items)}; processed: {len(res_items)}")

        return self.items
