import logging
import os

from platformdirs import PlatformDirs
from .version import __version__

dirs = PlatformDirs("chatinterface-client", "newguy103", version=__version__)


def simple_log_setup(
        log_file: str = '',
        log_level: int = logging.INFO, 

        log_format: str = '', 
        date_format: str = '',
) -> logging.Logger:
    if not log_format:
        log_format: str = "%(module)s: %(funcName)s - [%(asctime)s] - [%(levelname)s] - %(message)s"
    
    if not date_format:
        date_format: str = "%Y-%m-%d %H:%M:%S"

    if not log_file:
        log_file: str = os.path.join(dirs.user_data_dir, 'client.log')

    logger: logging.Logger = logging.Logger("chatinterface.client")
    formatter: logging.Formatter = logging.Formatter(log_format, date_format)

    console_handler: logging.StreamHandler = logging.StreamHandler()
    file_handler: logging.FileHandler = logging.FileHandler(log_file, encoding='utf-8')

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    logger.setLevel(log_level)
    return logger
