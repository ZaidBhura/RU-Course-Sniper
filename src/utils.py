"""Utility functions for configuration and helpers."""

import yaml
from pathlib import Path
from typing import List, Union, Dict, Any
from .models import WatchedIndex


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def parse_watched_indexes(config: Dict[str, Any]) -> List[WatchedIndex]:
    """Parse watched indexes from config, handling both int and dict formats."""
    watch_list = config.get('watch_indexes', [])
    watched = []
    
    for item in watch_list:
        if isinstance(item, int):
            watched.append(WatchedIndex(index=item))
        elif isinstance(item, dict):
            index = item.get('index')
            if index is None:
                raise ValueError(f"Invalid watch_indexes entry: {item} - missing 'index'")
            label = item.get('label')
            watched.append(WatchedIndex(index=int(index), label=label))
        else:
            raise ValueError(f"Invalid watch_indexes entry: {item} - must be int or dict")
    
    return watched


def build_webreg_url(index: int, semester_selection: str) -> str:
    """Build WebReg URL with prefilled index."""
    return f"https://sims.rutgers.edu/webreg/editSchedule.htm?login=cas&semesterSelection={semester_selection}&indexList={index}"

