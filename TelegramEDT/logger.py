import logging
from logging import handlers

log_format = "{%(levelname)s}[%(asctime)s]: %(name)s | %(message)s"

logging.basicConfig(
    format=log_format,
    level=logging.INFO
)
logger = logging.getLogger("TelegramEDT")
handler = handlers.TimedRotatingFileHandler("logs/current.log", when="d", interval=1)
handler.suffix = "%Y-%m-%d"
handler.style = log_format
handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(handler)
