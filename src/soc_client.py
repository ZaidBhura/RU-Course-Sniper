"""Client for interacting with Rutgers SOC API endpoints."""

import time
import requests
from typing import List, Optional, Dict, Any
from .models import OpenSection, CourseDetail


class SOCClient:
    """Client for Rutgers SOC API with retry logic and timeouts."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3, backoff_factor: float = 1.0):
        """
        Initialize SOC client.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            backoff_factor: Exponential backoff multiplier
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RutgersIndexSniper/1.0'
        })
    
    def _request_with_retry(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Make HTTP request with exponential backoff retry logic.
        
        Args:
            url: URL to fetch
            
        Returns:
            JSON response as dict, or None if all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries - 1:
                    # Last attempt failed
                    return None
                
                # Exponential backoff
                wait_time = self.backoff_factor * (2 ** attempt)
                time.sleep(wait_time)
        
        return None
    
    def fetch_open_sections(self, year: int = 2026, term: int = 1, campus: str = "NB") -> List[OpenSection]:
        """
        Fetch currently open sections.
        
        Args:
            year: Academic year
            term: Term number (1=Spring, 7=Fall, etc.)
            campus: Campus code (NB=New Brunswick)
            
        Returns:
            List of OpenSection objects, empty list on failure
        """
        url = f"https://sis.rutgers.edu/soc/api/openSections.json?year={year}&term={term}&campus={campus}"
        data = self._request_with_retry(url)
        
        if data is None:
            return []
        
        # Handle both list and dict responses
        if isinstance(data, list):
            sections = data
        elif isinstance(data, dict) and 'openSections' in data:
            sections = data['openSections']
        elif isinstance(data, str):
            # API might return a string (error message or HTML)
            print(f"[SOCClient] Warning: API returned string instead of JSON: {data[:100]}")
            return []
        else:
            print(f"[SOCClient] Warning: Unexpected API response type: {type(data)}")
            sections = []
        
        result = []
        for item in sections:
            try:
                # Handle both string and dict formats
                if isinstance(item, str):
                    # API returns index numbers as strings (e.g., "00053", "11671")
                    try:
                        index_num = int(item)
                        result.append(OpenSection(indexNumber=index_num))
                    except ValueError:
                        continue
                elif isinstance(item, dict):
                    # API might return dict with indexNumber field
                    result.append(OpenSection.from_api_data(item))
                else:
                    continue
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                # Log the error for debugging but continue
                print(f"[SOCClient] Error processing open section: {e}")
                continue
        
        return result
    
    def fetch_courses(self, year: int = 2026, term: int = 1, campus: str = "NB") -> Dict[int, CourseDetail]:
        """
        Fetch all course details and build index-to-detail mapping.
        
        Args:
            year: Academic year
            term: Term number
            campus: Campus code
            
        Returns:
            Dictionary mapping indexNumber -> CourseDetail, empty dict on failure
        """
        url = f"https://sis.rutgers.edu/soc/api/courses.json?year={year}&term={term}&campus={campus}"
        data = self._request_with_retry(url)
        
        if data is None:
            return {}
        
        # Handle both list and dict responses
        if isinstance(data, list):
            courses = data
        elif isinstance(data, dict) and 'courses' in data:
            courses = data['courses']
        elif isinstance(data, str):
            # API might return a string (error message or HTML)
            print(f"[SOCClient] Warning: API returned string instead of JSON: {data[:100]}")
            return {}
        else:
            print(f"[SOCClient] Warning: Unexpected API response type: {type(data)}")
            courses = []
        
        index_map = {}
        for course in courses:
            try:
                # Ensure course is a dict, not a string
                if not isinstance(course, dict):
                    continue
                
                # Courses may have multiple sections
                sections = course.get('sections', [])
                if not isinstance(sections, list):
                    continue
                    
                for section in sections:
                    # Ensure section is a dict
                    if not isinstance(section, dict):
                        continue
                        
                    index_num = section.get('index')
                    if index_num:
                        # Convert to int since API returns strings
                        try:
                            index_num = int(index_num)
                        except (ValueError, TypeError):
                            continue
                        
                        # Merge course-level and section-level data
                        # Extract instructor names from API response (list of dicts with 'name' field)
                        instructors_raw = section.get('instructors', [])
                        instructor_names = []
                        for instr in instructors_raw:
                            if isinstance(instr, dict) and 'name' in instr:
                                instructor_names.append(instr['name'])
                            elif isinstance(instr, str):
                                instructor_names.append(instr)
                        
                        # Extract meeting time descriptions from API response
                        meeting_times_raw = section.get('meetingTimes', [])
                        meeting_times = []
                        for mt in meeting_times_raw:
                            if isinstance(mt, dict):
                                # Build a readable meeting time string
                                parts = []
                                if mt.get('meetingDay'):
                                    parts.append(mt['meetingDay'])
                                if mt.get('startTime') and mt.get('endTime'):
                                    parts.append(f"{mt['startTime']}-{mt['endTime']}")
                                if mt.get('campusName'):
                                    parts.append(mt['campusName'])
                                if parts:
                                    meeting_times.append(" ".join(parts))
                            elif isinstance(mt, str):
                                meeting_times.append(mt)
                        
                        detail_data = {
                            'subject': course.get('subject', ''),
                            'courseNumber': course.get('courseNumber', ''),
                            'section': section.get('number', ''),
                            'title': course.get('title', ''),
                            'instructors': instructor_names,
                            'meetingTimes': meeting_times,
                            'indexNumber': index_num
                        }
                        index_map[index_num] = CourseDetail.from_api_data(detail_data)
            except (KeyError, TypeError, ValueError, AttributeError) as e:
                # Log the error for debugging but continue
                print(f"[SOCClient] Error processing course data: {e}")
                continue
        
        return index_map

