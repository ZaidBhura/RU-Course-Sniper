"""Main watcher logic for monitoring index availability."""

import time
from datetime import datetime
from typing import Set, Dict
from .models import WatchedIndex, OpenSection, NotificationPayload, CourseDetail
from .soc_client import SOCClient
from .enricher import CourseEnricher
from .notifier import Notifier
from .utils import build_webreg_url


class IndexWatcher:
    """Monitors watched indexes for availability changes."""
    
    def __init__(
        self,
        watched_indexes: list[WatchedIndex],
        soc_client: SOCClient,
        enricher: CourseEnricher,
        notifier: Notifier,
        poll_interval_seconds: int = 20,
        webreg_semester_selection: str = "12026"
    ):
        """
        Initialize watcher.
        
        Args:
            watched_indexes: List of WatchedIndex objects to monitor
            soc_client: SOCClient for API calls
            enricher: CourseEnricher for detail lookup
            notifier: Notifier for sending alerts
            poll_interval_seconds: How often to poll for changes
            webreg_semester_selection: Semester code for WebReg URLs
        """
        self.watched_indexes = {idx.index: idx for idx in watched_indexes}
        self.soc_client = soc_client
        self.enricher = enricher
        self.notifier = notifier
        self.poll_interval = poll_interval_seconds
        self.webreg_semester = webreg_semester_selection
        
        # Track which indexes are currently open (for state transitions)
        self.currently_open: Set[int] = set()
        
        # Track which indexes we've already notified about (to avoid duplicates)
        # Reset when index closes so we can notify again if it reopens
        self.notified_this_session: Set[int] = set()
        
        # Flag to control main loop
        self.running = True
    
    def _format_timestamp(self) -> str:
        """Get formatted timestamp string."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _check_availability(self, open_sections: list[OpenSection]) -> Set[int]:
        """
        Determine which watched indexes are currently open.
        
        Args:
            open_sections: List of currently open sections
            
        Returns:
            Set of watched index numbers that are open
        """
        open_indexes = {section.indexNumber for section in open_sections}
        watched_open = open_indexes & set(self.watched_indexes.keys())
        return watched_open
    
    def _handle_opened_indexes(self, newly_open: Set[int]):
        """
        Handle indexes that just opened.
        
        Args:
            newly_open: Set of index numbers that just became available
        """
        for index_num in newly_open:
            watched = self.watched_indexes[index_num]
            
            # Get course details if available
            course_detail: CourseDetail | None = self.enricher.get_detail(index_num)
            
            # Build WebReg URL
            webreg_url = build_webreg_url(index_num, self.webreg_semester)
            
            # Create notification payload
            payload = NotificationPayload(
                index=index_num,
                label=watched.label,
                course_detail=course_detail,
                webreg_url=webreg_url
            )
            
            # Send notification
            if course_detail:
                course_name = f"{course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
                label_str = f" ({watched.label})" if watched.label else ""
                print(f"[{self._format_timestamp()}] 🚨 ALERT: Index {index_num}{label_str} is now OPEN!")
                print(f"  Course: {course_name}")
                print(f"  Section: {course_detail.section}")
            else:
                label_str = f" ({watched.label})" if watched.label else ""
                print(f"[{self._format_timestamp()}] 🚨 ALERT: Index {index_num}{label_str} is now OPEN!")
                print(f"  (Course details loading...)")
            
            self.notifier.notify(payload)
            self.notified_this_session.add(index_num)
    
    def _handle_closed_indexes(self, newly_closed: Set[int]):
        """
        Handle indexes that just closed.
        
        Args:
            newly_closed: Set of index numbers that just became unavailable
        """
        for index_num in newly_closed:
            watched = self.watched_indexes.get(index_num)
            label_str = f" ({watched.label})" if watched and watched.label else ""
            
            # Get course name
            course_detail = self.enricher.get_detail(index_num)
            course_str = ""
            if course_detail:
                course_str = f" - {course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
            
            print(f"[{self._format_timestamp()}] ⚠️  Index {index_num}{label_str}{course_str} is now CLOSED")
            # Remove from notified set so we can notify again if it reopens
            self.notified_this_session.discard(index_num)
    
    def poll_once(self) -> bool:
        """
        Perform a single poll cycle.
        
        Returns:
            True if polling succeeded, False otherwise
        """
        try:
            open_sections = self.soc_client.fetch_open_sections()
            watched_open = self._check_availability(open_sections)
            
            # Detect state transitions
            newly_open = watched_open - self.currently_open
            newly_closed = self.currently_open - watched_open
            
            # Update state
            self.currently_open = watched_open
            
            # Handle transitions
            if newly_open:
                self._handle_opened_indexes(newly_open)
            
            if newly_closed:
                self._handle_closed_indexes(newly_closed)
            
            # Log status with course names
            timestamp = self._format_timestamp()
            open_count = len(watched_open)
            total_watched = len(self.watched_indexes)
            
            if watched_open:
                # Show which indexes are open with course names
                open_list = []
                for idx_num in sorted(watched_open):
                    watched = self.watched_indexes[idx_num]
                    course_detail = self.enricher.get_detail(idx_num)
                    if course_detail:
                        course_str = f"{course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
                        open_list.append(f"{idx_num} ({course_str})")
                    else:
                        open_list.append(str(idx_num))
                print(f"[{timestamp}] Poll complete: {open_count}/{total_watched} watched indexes are open")
                print(f"  Open: {', '.join(open_list)}")
            else:
                print(f"[{timestamp}] Poll complete: {open_count}/{total_watched} watched indexes are open")
            
            return True
            
        except Exception as e:
            print(f"[{self._format_timestamp()}] ERROR during poll: {e}")
            return False
    
    def run(self, enable_commands: bool = True):
        """
        Run the main polling loop.
        
        Args:
            enable_commands: If True, enable interactive command interface
        """
        print(f"[{self._format_timestamp()}] Starting Index Watcher")
        print(f"  Watching {len(self.watched_indexes)} index(es):")
        for idx in self.watched_indexes.values():
            label_str = f" ({idx.label})" if idx.label else ""
            
            # Get course details if available (may not be loaded yet)
            course_detail = self.enricher.get_detail(idx.index)
            course_str = ""
            if course_detail:
                course_str = f" - {course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
            
            print(f"    - Index {idx.index}{label_str}{course_str}")
        print(f"  Poll interval: {self.poll_interval} seconds")
        print(f"  WebReg semester: {self.webreg_semester}")
        print("")
        
        # Start enrichment in background
        self.enricher.start()
        
        # Start command handler if enabled
        command_handler = None
        if enable_commands:
            from .command_handler import CommandHandler
            command_handler = CommandHandler(self)
            command_handler.start()
        
        try:
            while self.running:
                self.poll_once()
                # Sleep in small increments to allow for quick shutdown
                for _ in range(self.poll_interval):
                    if not self.running:
                        break
                    time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{self._format_timestamp()}] Shutting down...")
            if command_handler:
                command_handler.stop()
            self.enricher.stop()
            print("  Enricher stopped")
            print("  Goodbye!")

