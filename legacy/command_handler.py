"""Interactive command handler for managing watched indexes."""

import threading
import time
from typing import List
from .models import WatchedIndex


class CommandHandler:
    """Handles interactive commands for managing the watchlist."""
    
    def __init__(self, watcher):
        """
        Initialize command handler.
        
        Args:
            watcher: IndexWatcher instance to manage
        """
        self.watcher = watcher
        self.running = False
        self.thread: threading.Thread | None = None
    
    def start(self):
        """Start the command handler in a background thread."""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._command_loop, daemon=True)
        self.thread.start()
        self._print_help()
    
    def stop(self):
        """Stop the command handler."""
        self.running = False
    
    def _print_help(self):
        """Print command help."""
        print("\n" + "="*60)
        print("INTERACTIVE COMMANDS AVAILABLE:")
        print("="*60)
        print("  add <index> [label]  - Add index to watchlist")
        print("                        Example: add 12345")
        print("                        Example: add 12345 \"My Course\"")
        print("  remove <index>       - Remove index from watchlist")
        print("                        Example: remove 12345")
        print("  list                 - Show all watched indexes")
        print("  help                 - Show this help message")
        print("  quit / exit          - Stop the application")
        print("="*60 + "\n")
    
    def _parse_add_command(self, parts: List[str]) -> WatchedIndex | None:
        """
        Parse 'add' command.
        
        Args:
            parts: Command parts (e.g., ['add', '12345', 'label'])
            
        Returns:
            WatchedIndex if valid, None otherwise
        """
        if len(parts) < 2:
            print("Error: Usage: add <index> [label]")
            return None
        
        try:
            index = int(parts[1])
        except ValueError:
            print(f"Error: '{parts[1]}' is not a valid index number")
            return None
        
        # Get label if provided
        label = None
        if len(parts) > 2:
            # Join remaining parts as label (handles quoted labels with spaces)
            label = " ".join(parts[2:]).strip('"\'')
        
        return WatchedIndex(index=index, label=label)
    
    def _parse_remove_command(self, parts: List[str]) -> int | None:
        """
        Parse 'remove' command.
        
        Args:
            parts: Command parts (e.g., ['remove', '12345'])
            
        Returns:
            Index number if valid, None otherwise
        """
        if len(parts) < 2:
            print("Error: Usage: remove <index>")
            return None
        
        try:
            return int(parts[1])
        except ValueError:
            print(f"Error: '{parts[1]}' is not a valid index number")
            return None
    
    def _handle_add(self, parts: List[str]):
        """Handle 'add' command."""
        watched = self._parse_add_command(parts)
        if watched is None:
            return
        
        # Check if already watching
        if watched.index in self.watcher.watched_indexes:
            existing = self.watcher.watched_indexes[watched.index]
            existing_course = self.watcher.enricher.get_detail(existing.index)
            label_str = f" (label: {existing.label})" if existing.label else ""
            course_str = ""
            if existing_course:
                course_str = f" - {existing_course.subject} {existing_course.courseNumber}: {existing_course.title}"
            print(f"Index {watched.index}{label_str}{course_str} is already being watched")
            return
        
        # Add to watchlist
        self.watcher.watched_indexes[watched.index] = watched
        label_str = f" (label: {watched.label})" if watched.label else ""
        
        # Try to get course name immediately
        course_detail = self.watcher.enricher.get_detail(watched.index)
        course_str = ""
        if course_detail:
            course_str = f" - {course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
            print(f"[SUCCESS] Added index {watched.index}{label_str}{course_str} to watchlist")
        else:
            # Course details not yet available
            print(f"[SUCCESS] Added index {watched.index}{label_str} to watchlist")
            print(f"         Course name will be displayed once details are loaded (may take a moment)...")
        
        # Check if this index is currently open and notify immediately
        if watched.index in self.watcher.currently_open:
            print(f"\n[NOTIFICATION] Index {watched.index} is already OPEN! Sending Discord alert...")
            from .models import NotificationPayload
            from .utils import build_webreg_url
            
            webreg_url = build_webreg_url(watched.index, self.watcher.webreg_semester)
            payload = NotificationPayload(
                index=watched.index,
                label=watched.label,
                course_detail=course_detail,
                webreg_url=webreg_url
            )
            self.watcher.notifier.notify(payload)
            self.watcher.notified_this_session.add(watched.index)
    
    def _handle_remove(self, parts: List[str]):
        """Handle 'remove' command."""
        index = self._parse_remove_command(parts)
        if index is None:
            return
        
        if index not in self.watcher.watched_indexes:
            print(f"Index {index} is not in the watchlist")
            return
        
        # Get course name before removing
        course_detail = self.watcher.enricher.get_detail(index)
        course_str = ""
        if course_detail:
            course_str = f" ({course_detail.subject} {course_detail.courseNumber}: {course_detail.title})"
        
        del self.watcher.watched_indexes[index]
        # Also remove from state tracking
        self.watcher.currently_open.discard(index)
        self.watcher.notified_this_session.discard(index)
        print(f"[SUCCESS] Removed index {index}{course_str} from watchlist")
        print(f"[SUCCESS] Removed index {index}{course_str} from watchlist")
    
    def _handle_list(self):
        """Handle 'list' command."""
        if not self.watcher.watched_indexes:
            print("No indexes are currently being watched")
            return
        
        print("\nCurrently watched indexes:")
        print("-" * 80)
        for idx in sorted(self.watcher.watched_indexes.values(), key=lambda x: x.index):
            status = "OPEN" if idx.index in self.watcher.currently_open else "CLOSED"
            label_str = f" - {idx.label}" if idx.label else ""
            
            # Get course details if available
            course_detail = self.watcher.enricher.get_detail(idx.index)
            course_str = ""
            if course_detail:
                course_str = f" | {course_detail.subject} {course_detail.courseNumber}: {course_detail.title}"
            
            print(f"  {idx.index:5d} [{status:6s}]{label_str}{course_str}")
        print("-" * 80 + "\n")
    
    def _command_loop(self):
        """Main command loop running in background thread."""
        import sys
        while self.running:
            try:
                # Read input from stdin
                # This will block, but that's okay since it's in a separate thread
                if sys.stdin.isatty():
                    command = input().strip()
                else:
                    # If stdin is not a TTY, skip command handling
                    time.sleep(1)
                    continue
                
                if not command:
                    continue
                
                parts = command.split()
                cmd = parts[0].lower()
                
                if cmd == "add":
                    self._handle_add(parts)
                elif cmd == "remove":
                    self._handle_remove(parts)
                elif cmd == "list":
                    self._handle_list()
                elif cmd in ("help", "?"):
                    self._print_help()
                elif cmd in ("quit", "exit", "stop"):
                    print("\nStopping application...")
                    # Signal main thread to stop by setting running flag
                    self.running = False
                    self.watcher.running = False
                    # Raise KeyboardInterrupt in main thread
                    import _thread
                    _thread.interrupt_main()
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")
            except EOFError:
                # Input stream closed
                break
            except KeyboardInterrupt:
                # User pressed Ctrl+C
                self.running = False
                break
            except Exception as e:
                print(f"Error processing command: {e}")

