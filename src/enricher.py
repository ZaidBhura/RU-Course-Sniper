"""Course detail enrichment with caching."""

import time
import threading
from typing import Dict, Optional
from .models import CourseDetail
from .soc_client import SOCClient


class CourseEnricher:
    """Manages course detail enrichment with periodic caching."""
    
    def __init__(self, soc_client: SOCClient, cache_interval_seconds: int = 600):
        """
        Initialize enricher.
        
        Args:
            soc_client: SOCClient instance for API calls
            cache_interval_seconds: How often to refresh course details (default 10 minutes)
        """
        self.soc_client = soc_client
        self.cache_interval = cache_interval_seconds
        self.index_to_detail: Dict[int, CourseDetail] = {}
        self.last_fetch_time: float = 0
        self.lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
    
    def start(self):
        """Start background thread for periodic enrichment."""
        if self.running:
            return
        
        self.running = True
        print("[Enricher] Starting course detail enrichment...")
        # Initial fetch - do this synchronously to ensure data is available
        self._refresh_cache()
        print(f"[Enricher] Initial fetch complete. Loaded {len(self.index_to_detail)} course indexes.")
        
        # Start background thread for periodic refreshes
        self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop background enrichment thread."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5.0)
    
    def _refresh_loop(self):
        """Background loop to periodically refresh course details."""
        while self.running:
            time.sleep(self.cache_interval)
            if self.running:
                self._refresh_cache()
    
    def _refresh_cache(self):
        """Fetch and update course details cache."""
        try:
            print("[Enricher] Fetching course details from SOC API...")
            new_map = self.soc_client.fetch_courses()
            with self.lock:
                self.index_to_detail = new_map
                self.last_fetch_time = time.time()
            print(f"[Enricher] Successfully loaded {len(new_map)} course details from API")
        except Exception as e:
            # Log but don't crash - enrichment is optional
            print(f"[Enricher] Failed to refresh course details: {e}")
    
    def get_detail(self, index: int) -> Optional[CourseDetail]:
        """
        Get course detail for an index number.
        
        Args:
            index: Index number to look up
            
        Returns:
            CourseDetail if available, None otherwise
        """
        with self.lock:
            return self.index_to_detail.get(index)
    
    def get_cache_age_seconds(self) -> float:
        """Get age of current cache in seconds."""
        with self.lock:
            if self.last_fetch_time == 0:
                return float('inf')
            return time.time() - self.last_fetch_time

