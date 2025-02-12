from datetime import datetime
import logging
import os
from pathlib import Path


def setup_logging(logging_level=logging.INFO):
    logger = logging.getLogger(__name__)
    dir_path = Path(os.path.dirname(os.path.realpath(__file__)))

    if not os.path.exists(dir_path / "logs"):
        os.mkdir(dir_path / "logs")

    if not os.path.exists(dir_path / "calibration"):
        os.mkdir(dir_path / "calibration")

    log_formatter = logging.Formatter(
        "%(asctime)s.%(msecs)03d %(levelname)s %(filename)s %(lineno)s | %(message)s"
    )

    file_handler = logging.FileHandler(
        f"{dir_path}/logs/{datetime.now().strftime('%Y%m%d%H%M%S')}.log"
    )
    file_handler.setFormatter(log_formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    logger.addHandler(console_handler)
    logger.setLevel(logging_level)

    return logger
