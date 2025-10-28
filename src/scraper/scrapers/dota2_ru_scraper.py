import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Dict, List

import requests
from bs4 import BeautifulSoup, Tag

from scraper.dota.types import Buffs, DotaItem
from scraper.dota.utils import parse_buffs


class Dota2RuScraper:
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/114.0.0.0 Safari/537.36"
        )
    }

    def __init__(self) -> None:
        pass

    def _process_item(self, item: Tag) -> DotaItem | None:
        try:
            descr_block = item.find("div", class_="base-items__shop-descr-top")
            if not isinstance(descr_block, Tag):
                return None

            p_tags = descr_block.find_all("p")
            name_tag = p_tags[0] if len(p_tags) > 0 else None
            item_name = name_tag.text.strip() if name_tag else None
            if not item_name:
                return None

            cost = 0
            if len(p_tags) > 1:
                cost_tag = p_tags[1]
                cost = int(cost_tag.text.strip().replace(" ", "")) if cost_tag else 0

            a_tag = item.find("a")
            if not isinstance(a_tag, Tag):
                return None

            item_url = a_tag.get("href")
            if not isinstance(item_url, str):
                return None
            item_url = "https://dota2.ru" + item_url

            img_tag = a_tag.find("img", class_="base-items__shop-img")
            if not isinstance(img_tag, Tag):
                return None

            img_url = img_tag.get("src")
            if not isinstance(img_url, str):
                return None
            img_url = "https://dota2.ru" + re.sub(r"\.webp\??\d*", ".jpg", img_url)

            recipe = self._scrape_recipe(item_url)
            if recipe is None:
                return None

            buffs = None
            try:
                buffs = self._scrape_buffs(item)
            except Exception as e:
                print(f"[WARN] ERROR processing buffs: {e}")

            return DotaItem(
                name=item_name,
                cost=cost,
                url=item_url,
                image=img_url,
                recipe=recipe,
                buffs=buffs,
            )

        except Exception as e:
            print(f"ERROR processing item: {e}")
            return None

    def scrape(self) -> Dict[str, DotaItem]:
        ans: Dict[str, DotaItem] = {}

        response = requests.get("https://dota2.ru/items/", headers=self.HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        shop_items_block = soup.find("div", class_="base-items__block-shop")
        if shop_items_block is None or not isinstance(shop_items_block, Tag):
            return {}

        items = shop_items_block.find_all(
            "li", class_="base-items__shop-item js-items-filter-item"
        )

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(self._process_item, item)
                for item in items
                if isinstance(item, Tag)
            ]

            for future in as_completed(futures):
                result = future.result()
                if result:
                    # print(f"DEBUG: fetched {result.name}")
                    ans[result.name] = result

        return ans

    def _scrape_buffs(self, item: Tag) -> Buffs:
        attributes_div = item.select_one('div[class="attributes"]')
        if not attributes_div:
            return Buffs()
        apparent_text = attributes_div.get_text(" ", strip=True)
        return parse_buffs(
            [("+" + l.strip()) for l in apparent_text.split("+") if l.strip()]
        )

    def _scrape_recipe(self, url: str) -> List[str] | None:
        response = requests.get(url, headers=self.HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        base_blocks = soup.find_all("div", class_="base-items__shop-descr-comp")
        base_block: Tag | None = None
        for block in base_blocks:
            if not block or not isinstance(block, Tag):
                continue
            block_title_tag = block.find("h4")
            if block_title_tag is None or not isinstance(block_title_tag, Tag):
                continue
            block_title = block_title_tag.text
            if not isinstance(block_title, str):
                continue

            if "компоненты" in block_title.lower():
                base_block = block
                break

        if not base_block or not isinstance(base_block, Tag):
            return []

        children = base_block.find_all("li")
        if not children:
            return None

        res: List[str] = []
        for child in children:
            if not isinstance(child, Tag):
                continue

            # check if recipe
            img_tag = child.find("img")
            if not img_tag or not isinstance(img_tag, Tag):
                continue
            img_url = img_tag.get("src")
            if not isinstance(img_url, str):
                continue
            if "recipe" in img_url.lower():
                res.append("Recipe")
                continue

            a_tag = child.find("a")
            if not a_tag or not isinstance(a_tag, Tag):
                continue
            a_url = a_tag.get("href")
            if not isinstance(a_url, str):
                continue
            item_name = self._scrape_item_name("https://dota2.ru" + a_url)
            if not item_name:
                continue
            res.append(item_name)

        return res

    @lru_cache()
    def _scrape_item_name(self, url: str) -> str | None:
        response = requests.get(url, headers=self.HEADERS)
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1", class_="title-global")
        if not title_tag or not isinstance(title_tag, Tag):
            return None
        title = title_tag.text
        return title.strip() if isinstance(title, str) else None
