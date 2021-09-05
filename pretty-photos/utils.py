import logging
import shutil
import typing as _t
from pathlib import Path


def get_console_logger(name: _t.Optional[str] = None) -> logging.Logger:
    """Get simple console logger with custom name"""
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s")
    handler.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)

    return logger


def get_extension_from_path(path: Path) -> str:
    return path.suffix[1:]


def try_mkdir(dir_path: Path) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def copy_file(input_path: Path, output_path: Path) -> None:
    shutil.copy(str(input_path), str(output_path))
