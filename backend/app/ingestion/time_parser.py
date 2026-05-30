import re
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass

@dataclass
class TimeRange:
    start: float  # seconds
    end: float    # seconds
    original_query: str = ""
    fuzzy: bool = False

class TimeParser:
    """
    Parse natural language time queries from videos.
    Supports exact timestamps, ranges, fuzzy matches, and implied sections.
    """
    
    def __init__(self, default_buffer: float = 5.0, fuzzy_buffer: float = 10.0):
        self.default_buffer = default_buffer
        self.fuzzy_buffer = fuzzy_buffer
        
        # Pre-defined section mappings (implied timeframes)
        self.section_mappings = {
            'opening': (0, 15),
            'intro': (0, 15),
            'start': (0, 10),
            'beginning': (0, 10),
            'middle': (0.3, 0.7),  # Percentage-based
            'mid': (0.3, 0.7),
            'ending': (-15, 0),    # Last 15 seconds
            'outro': (-15, 0),
            'end': (-10, 0),
            'conclusion': (-20, 0)
        }
    
    def parse(self, query: str, video_duration: float) -> Optional[TimeRange]:
        """
        Parse time query and return TimeRange.
        Returns None if no time component found.
        """
        query_lower = query.lower()
        
        # Check for implied sections first
        section_time = self._parse_implied_section(query_lower, video_duration)
        if section_time:
            return section_time
        
        # Check for percentage-based ("first 25%")
        percentage_time = self._parse_percentage(query_lower, video_duration)
        if percentage_time:
            return percentage_time
        
        # Check for exact timestamps ("at 1:30")
        timestamp_time = self._parse_timestamp(query_lower, video_duration)
        if timestamp_time:
            return timestamp_time
        
        # Check for ranges ("between 1:00 and 2:00")
        range_time = self._parse_range(query_lower, video_duration)
        if range_time:
            return range_time
        
        # Check for fuzzy matches ("around 2 minutes")
        fuzzy_time = self._parse_fuzzy(query_lower, video_duration)
        if fuzzy_time:
            return fuzzy_time
        
        # Check for simple duration ("first 5 seconds", "first 2 minutes")
        duration_time = self._parse_duration(query_lower, video_duration)
        if duration_time:
            return duration_time
        
        # Check for near-end ("last 10 seconds")
        near_end_time = self._parse_near_end(query_lower, video_duration)
        if near_end_time:
            return near_end_time
        
        return None
    
    def _parse_implied_section(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse implied sections like 'opening', 'middle', 'outro'"""
        for section, value in self.section_mappings.items():
            if section in query:
                if isinstance(value, tuple):
                    if value[0] < 0:  # Negative means from end
                        start = max(0, duration + value[0])
                        end = duration
                    elif value[1] <= 1:  # Percentage-based (0-1 range)
                        start = duration * value[0]
                        end = duration * value[1]
                    else:  # Absolute seconds
                        start = value[0]
                        end = min(duration, value[1])
                    return TimeRange(start=start, end=end, original_query=query)
        return None
    
    def _parse_percentage(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse 'first 25%', 'last 50%', etc."""
        # First X%
        match = re.search(r'first\s+(\d+(?:\.\d+)?)\s*%', query)
        if match:
            percent = float(match.group(1)) / 100
            return TimeRange(start=0, end=duration * percent, original_query=query)
        
        # Last X%
        match = re.search(r'last\s+(\d+(?:\.\d+)?)\s*%', query)
        if match:
            percent = float(match.group(1)) / 100
            return TimeRange(start=duration * (1 - percent), end=duration, original_query=query)
        
        return None
    
    def _parse_timestamp(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse 'at 1:30', 'at 1 minute 30 seconds'"""
        # mm:ss format
        match = re.search(r'(?:at|around|about)?\s*(\d{1,2}):(\d{2})', query)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2))
            timestamp = minutes * 60 + seconds
            
            buffer = self.default_buffer
            if 'around' in query or 'about' in query:
                buffer = self.fuzzy_buffer
            
            return TimeRange(
                start=max(0, timestamp - buffer),
                end=min(duration, timestamp + buffer),
                original_query=query,
                fuzzy=('around' in query or 'about' in query)
            )
        
        # X minutes Y seconds format
        match = re.search(r'(\d+)\s*(?:minutes?|mins?)(?:\s*(\d+)\s*seconds?)?', query)
        if match:
            minutes = int(match.group(1))
            seconds = int(match.group(2)) if match.group(2) else 0
            timestamp = minutes * 60 + seconds
            
            buffer = self.default_buffer
            if 'around' in query or 'about' in query:
                buffer = self.fuzzy_buffer
            
            return TimeRange(
                start=max(0, timestamp - buffer),
                end=min(duration, timestamp + buffer),
                original_query=query
            )
        
        return None
    
    def _parse_range(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse 'between 1:00 and 2:00'"""
        pattern = r'between\s+(\d{1,2}:\d{2})\s+and\s+(\d{1,2}:\d{2})'
        match = re.search(pattern, query)
        if match:
            start_mmss = match.group(1)
            end_mmss = match.group(2)
            
            start_parts = start_mmss.split(':')
            end_parts = end_mmss.split(':')
            
            start = int(start_parts[0]) * 60 + int(start_parts[1])
            end = int(end_parts[0]) * 60 + int(end_parts[1])
            
            return TimeRange(start=start, end=end, original_query=query)
        
        return None
    
    def _parse_fuzzy(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse 'around 2 minutes', 'about 30 seconds in'"""
        match = re.search(r'(?:around|about|roughly|approximately)\s+(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|seconds?|secs?)', query)
        if match:
            value = float(match.group(1))
            unit = 'minutes' if 'min' in query else 'seconds'
            
            if unit == 'minutes':
                timestamp = value * 60
            else:
                timestamp = value
            
            return TimeRange(
                start=max(0, timestamp - self.fuzzy_buffer),
                end=min(duration, timestamp + self.fuzzy_buffer),
                original_query=query,
                fuzzy=True
            )
        
        return None
    
    def _parse_duration(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse 'first 5 seconds', 'first 2 minutes'"""
        
        match = re.search(r'first\s+(\d+(?:\.\d+)?)\s+seconds?', query)
        if match:
            seconds = float(match.group(1))
            return TimeRange(start=0, end=min(duration, seconds), original_query=query)
        
        
        match = re.search(r'first\s+(\d+(?:\.\d+)?)\s+minutes?', query)
        if match:
            minutes = float(match.group(1))
            return TimeRange(start=0, end=min(duration, minutes * 60), original_query=query)
        
        return None
    
    def _parse_near_end(self, query: str, duration: float) -> Optional[TimeRange]:
        """Parse 'last 10 seconds', 'towards the end'"""
        
        match = re.search(r'last\s+(\d+(?:\.\d+)?)\s+seconds?', query)
        if match:
            seconds = float(match.group(1))
            return TimeRange(start=max(0, duration - seconds), end=duration, original_query=query)
        
        
        if 'towards the end' in query or 'near the end' in query:
            return TimeRange(start=max(0, duration - 30), end=duration, original_query=query)
        
        return None
    
    def expand_range(self, time_range: TimeRange, percent: float = 20, duration: float = None) -> TimeRange:
        """Expand a time range by percentage (for fallback retrieval)"""
        current_span = time_range.end - time_range.start
        expansion = current_span * (percent / 100)
        
        new_start = max(0, time_range.start - expansion)
        new_end = min(duration, time_range.end + expansion) if duration else time_range.end + expansion
        
        return TimeRange(start=new_start, end=new_end, original_query=time_range.original_query, fuzzy=time_range.fuzzy)



time_parser = TimeParser()