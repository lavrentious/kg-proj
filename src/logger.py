import logging

logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)


def getLogger(name: str) -> logging.Logger:
    return logging.getLogger(name)
