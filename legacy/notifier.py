"""Notification handlers for Discord and Pushover."""

import os
import json
import requests
from typing import Optional
from .models import NotificationPayload, CourseDetail


class Notifier:
    """Handles sending notifications via Discord and Pushover."""
    
    def __init__(self):
        """Initialize notifier with credentials from environment."""
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.pushover_token = os.getenv('PUSHOVER_TOKEN')
        self.pushover_user = os.getenv('PUSHOVER_USER')
    
    def format_message(self, payload: NotificationPayload) -> str:
        """
        Format notification message for readability.
        
        Args:
            payload: Notification payload with index and details
            
        Returns:
            Formatted message string
        """
        lines = []
        
        # WebReg link at the top for quick access
        lines.append(f"🔗 **WebReg Link:** {payload.webreg_url}")
        lines.append("")
        
        # Index with course name prominently displayed
        if payload.course_detail:
            detail = payload.course_detail
            course_name = f"{detail.subject} {detail.courseNumber}: {detail.title}"
            if payload.label:
                lines.append(f"**Index {payload.index}** ({payload.label})")
            else:
                lines.append(f"**Index {payload.index}**")
            lines.append(f"**{course_name}**")
            lines.append(f"Section: {detail.section}")
        else:
            # No course details available yet
            if payload.label:
                lines.append(f"**Index:** {payload.index} ({payload.label})")
            else:
                lines.append(f"**Index:** {payload.index}")
            lines.append("_Course details loading..._")
        
        # Additional course details if available
        if payload.course_detail:
            detail = payload.course_detail
            if detail.instructors:
                instructors_str = ", ".join(str(i) for i in detail.instructors)
                lines.append(f"**Instructor(s):** {instructors_str}")
            
            if detail.meetingTimes:
                times_str = " | ".join(str(t) for t in detail.meetingTimes)
                lines.append(f"**Meeting Times:** {times_str}")
        
        return "\n".join(lines)
    
    def send_discord(self, payload: NotificationPayload) -> bool:
        """
        Send notification via Discord webhook.
        
        Args:
            payload: Notification payload
            
        Returns:
            True if successful, False otherwise
        """
        if not self.discord_webhook_url:
            return False
        
        try:
            message = self.format_message(payload)
            
            # Discord webhook payload with course name in title
            if payload.course_detail:
                title = f"Index {payload.index}: {payload.course_detail.subject} {payload.course_detail.courseNumber}"
            else:
                title = f"Index {payload.index} Available"
            
            discord_payload = {
                "content": f"🚨 **INDEX {payload.index} IS NOW OPEN!** 🚨",
                "embeds": [{
                    "title": title,
                    "description": message,
                    "color": 0x00ff00,  # Green
                    "timestamp": None
                }]
            }
            
            response = requests.post(
                self.discord_webhook_url,
                json=discord_payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Notifier] Discord notification failed: {e}")
            return False
    
    def send_pushover(self, payload: NotificationPayload) -> bool:
        """
        Send notification via Pushover.
        
        Args:
            payload: Notification payload
            
        Returns:
            True if successful, False otherwise
        """
        if not self.pushover_token or not self.pushover_user:
            return False
        
        try:
            message = self.format_message(payload)
            
            # Pushover API payload
            pushover_payload = {
                "token": self.pushover_token,
                "user": self.pushover_user,
                "title": f"Index {payload.index} Available",
                "message": message,
                "priority": 1,  # High priority
                "url": payload.webreg_url,
                "url_title": "Open WebReg"
            }
            
            response = requests.post(
                "https://api.pushover.net/1/messages.json",
                data=pushover_payload,
                timeout=10
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"[Notifier] Pushover notification failed: {e}")
            return False
    
    def notify(self, payload: NotificationPayload):
        """
        Send notifications via all configured channels.
        
        Args:
            payload: Notification payload
        """
        discord_sent = self.send_discord(payload)
        pushover_sent = self.send_pushover(payload)
        
        if not discord_sent and not pushover_sent:
            print(f"[Notifier] WARNING: No notifications sent for index {payload.index}")

