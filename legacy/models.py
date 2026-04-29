"""Data models for the Rutgers Index Course Sniper."""

from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class WatchedIndex:
    """Represents an index number being watched."""
    index: int
    label: Optional[str] = None

    def __hash__(self) -> int:
        return hash(self.index)

    def __eq__(self, other) -> bool:
        if isinstance(other, WatchedIndex):
            return self.index == other.index
        return False


@dataclass
class CourseDetail:
    """Course details from the courses.json API."""
    subject: str
    courseNumber: str
    section: str
    title: str
    instructors: List[str]
    meetingTimes: List[str]
    indexNumber: int

    @classmethod
    def from_api_data(cls, data: dict) -> 'CourseDetail':
        """Create CourseDetail from API response data."""
        return cls(
            subject=data.get('subject', ''),
            courseNumber=data.get('courseNumber', ''),
            section=data.get('section', ''),
            title=data.get('title', ''),
            instructors=data.get('instructors', []),
            meetingTimes=data.get('meetingTimes', []),
            indexNumber=data.get('indexNumber', 0)
        )


@dataclass
class OpenSection:
    """Represents an open section from openSections.json."""
    indexNumber: int

    @classmethod
    def from_api_data(cls, data: dict) -> 'OpenSection':
        """Create OpenSection from API response data."""
        return cls(indexNumber=data.get('indexNumber', 0))


@dataclass
class NotificationPayload:
    """Payload for sending notifications."""
    index: int
    label: Optional[str]
    course_detail: Optional[CourseDetail]
    webreg_url: str

