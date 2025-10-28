from scraper.dota.utils import save_to_json, set_orders
from scraper.scrapers.dota2_ru_scraper import Dota2RuScraper

# use Dota2RuScraper, Fandom has outdated recipes
scraper = Dota2RuScraper()


# parse existing
# res = parse_from_json("dota_items.json")

# scrape from site
res = scraper.scrape()


print(len(res.values()))
res = set_orders(res)  # assign orders
save_to_json("items.json", res)
