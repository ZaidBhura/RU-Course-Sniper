"""Main entry point for Rutgers Index Course Sniper."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

from .soc_client import SOCClient
from .enricher import CourseEnricher
from .notifier import Notifier
from .watcher import IndexWatcher
from .utils import load_config, parse_watched_indexes


def main():
    """Main entry point."""
    # Load environment variables
    env_path = Path(".env")
    if env_path.exists():
        load_dotenv(env_path)
    else:
        print("Warning: .env file not found. Discord notifications may not work.")
    
    # Load configuration
    try:
        config = load_config("config.yaml")
    except FileNotFoundError:
        print("Error: config.yaml not found. Please copy config.yaml.example to config.yaml")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config.yaml: {e}")
        sys.exit(1)
    
    # Parse configuration
    try:
        watched_indexes = parse_watched_indexes(config)
        if not watched_indexes:
            print("Error: No indexes specified in watch_indexes")
            sys.exit(1)
        
        poll_interval = config.get('poll_interval_seconds', 20)
        webreg_semester = config.get('webreg_semester_selection', '12026')
        
    except Exception as e:
        print(f"Error parsing configuration: {e}")
        sys.exit(1)
    
    # Initialize components
    soc_client = SOCClient(timeout=10, max_retries=3)
    enricher = CourseEnricher(soc_client, cache_interval_seconds=600)
    notifier = Notifier()
    
    # Create and run watcher
    watcher = IndexWatcher(
        watched_indexes=watched_indexes,
        soc_client=soc_client,
        enricher=enricher,
        notifier=notifier,
        poll_interval_seconds=poll_interval,
        webreg_semester_selection=webreg_semester
    )
    
    watcher.run()


if __name__ == "__main__":
    main()

