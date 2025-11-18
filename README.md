<h3 style="text-align: center;">Онтология по Dota 2</h3>
<p style="text-align: center; color: #999;">Графы знаний, 2025</p>

В этом репозитории содержится код для парсинга данных и заполнения онтологии

# 0. Установка
1. `poetry install`
2. `source $(poetry env info --path)/bin/activate`

# 1. Парсинг
Онтология строится по базе данных предметов. Их данные парсятся с `dota2.ru` / `dota2.fandom.com`.


Следует воспользоваться скриптом `scraper.py`, который парсит данные и собирает их в `.json`:
```bash
python src/scraper.py --output items.json
```


\### in progress ###
