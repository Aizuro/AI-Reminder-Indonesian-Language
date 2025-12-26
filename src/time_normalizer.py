"""
Time Normalization Logic - UPDATED VERSION
Added support for relative time ("X menit lagi", "X jam lagi")
"""

from datetime import datetime, timedelta
import pytz
from typing import List, Dict
import re


class TimeNormalizer:
    """Normalize extracted time entities to datetime"""

    def __init__(self, timezone: str = "Asia/Jakarta"):
        """
        Initialize TimeNormalizer

        Args:
            timezone (str): Timezone string (default: Asia/Jakarta)
        """
        self.timezone = pytz.timezone(timezone)

        # Time ranges untuk context (pagi, siang, sore, malam)
        self.time_ranges = {
            'pagi': (1, 11),
            'siang': (11, 15),
            'sore': (15, 18),
            'malam': (18, 12)
        }

    def normalize(self, text: str, entities: List[Dict]) -> datetime:
        """
        Normalize time entities to datetime object

        Args:
            text (str): Original user input text
            entities (list): List of detected entities from NER model

        Returns:
            datetime: Target datetime untuk reminder
        """

        # Get current time
        now = datetime.now(self.timezone)
        text_lower = text.lower()

        # NEW: Check for relative time ("X menit lagi", "X jam lagi", "X detik lagi")
        relative_time = self._extract_relative_time(text_lower)
        if relative_time:
            print(f"DEBUG: Using relative time: +{relative_time} seconds")
            return now + timedelta(seconds=relative_time)

        # Extract time components
        hour, minute = self._extract_time(text_lower)

        # Determine target date
        target_date = self._determine_date(text_lower, now)

        # Adjust hour based on context
        hour = self._adjust_hour_by_context(text_lower, hour)

        # Create datetime
        try:
            result = target_date.replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )

            # Auto-adjust if time is in the past
            has_explicit_date = any(word in text_lower for word in [
                'besok', 'lusa', 'senin', 'selasa', 'rabu', 'kamis',
                'jumat', 'sabtu', 'minggu', 'kemarin'
            ])

            if not has_explicit_date and result <= now:
                print(
                    f"DEBUG: Time {result} is in the past, adjusting to next day")
                result = result + timedelta(days=1)

            return result

        except ValueError as e:
            print(f"ERROR: {e}, using fallback time")
            return now + timedelta(hours=1)

    def _extract_relative_time(self, text: str) -> int:
        """
        Extract relative time duration (e.g., "5 menit lagi", "2 jam lagi")

        Returns:
            int: Total seconds to add, or 0 if no relative time found

        Supported patterns:
        - "X detik lagi" → X seconds
        - "X menit lagi" → X minutes
        - "X jam lagi" → X hours
        - "X hari lagi" → X days

        Examples:
            "reminder 5 menit lagi" → 300 seconds
            "alarm 2 jam lagi" → 7200 seconds
            "meeting 30 detik lagi" → 30 seconds
        """

        # Pattern: angka + unit + "lagi"

        # Try detik (seconds)
        match = re.search(r'(\d+)\s*detik\s*lagi', text)
        if match:
            seconds = int(match.group(1))
            print(f"DEBUG: Found '{seconds} detik lagi'")
            return seconds

        # Try menit (minutes)
        match = re.search(r'(\d+)\s*menit\s*lagi', text)
        if match:
            minutes = int(match.group(1))
            print(f"DEBUG: Found '{minutes} menit lagi'")
            return minutes * 60

        # Try jam (hours)
        match = re.search(r'(\d+)\s*jam\s*lagi', text)
        if match:
            hours = int(match.group(1))
            print(f"DEBUG: Found '{hours} jam lagi'")
            return hours * 3600

        # Try hari (days)
        match = re.search(r'(\d+)\s*hari\s*lagi', text)
        if match:
            days = int(match.group(1))
            print(f"DEBUG: Found '{days} hari lagi'")
            return days * 86400

        # No relative time found
        return 0

    def _extract_time(self, text: str) -> tuple:
        """Extract hour and minute from text using regex"""

        # Clean tokenizer artifacts
        text_clean = text.replace(' . ', '.').replace(' : ', ':')
        text_clean = text_clean.replace(' .', '.').replace(': ', ':')

        # Pattern 1: "pukul 09:30" or "jam 09:30"
        time_pattern = r'(?:pukul|jam)?\s*(\d{1,2})[\:\.\,](\d{2})'
        match = re.search(time_pattern, text_clean)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            print(
                f"DEBUG: Extracted from '{text_clean}' → {hour}:{minute:02d}")
            return hour, minute

        # Pattern 2: "jam 9" or "pukul 14"
        time_pattern_hour = r'(?:pukul|jam)\s+(\d{1,2})(?!\d)'
        match = re.search(time_pattern_hour, text_clean)
        if match:
            hour = int(match.group(1))
            print(f"DEBUG: Extracted hour only → {hour}:00")
            return hour, 0

        # Pattern 3: Angka + time of day
        number_pattern = r'(\d{1,2})\s*(?:pagi|siang|sore|malam)'
        match = re.search(number_pattern, text_clean)
        if match:
            hour = int(match.group(1))
            return hour, 0

        # Pattern 4: Time of day only
        if 'pagi' in text:
            return 8, 0
        elif 'siang' in text:
            return 12, 0
        elif 'sore' in text:
            return 16, 0
        elif 'malam' in text:
            return 19, 0

        # Default
        return 9, 0

    def _determine_date(self, text: str, now: datetime) -> datetime:
        """Determine target date from text"""

        # Relative dates
        if 'besok' in text:
            return now + timedelta(days=1)
        elif 'lusa' in text:
            return now + timedelta(days=2)
        elif 'kemarin' in text:
            return now - timedelta(days=1)

        # Day names
        day_names = {
            'senin': 0, 'selasa': 1, 'rabu': 2, 'kamis': 3,
            'jumat': 4, 'sabtu': 5, 'minggu': 6
        }

        for day_name, day_num in day_names.items():
            if day_name in text:
                days_ahead = day_num - now.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                return now + timedelta(days=days_ahead)

        # Default: hari ini
        return now

    def _adjust_hour_by_context(self, text: str, hour: int) -> int:
        """Adjust hour based on context words (pagi, siang, sore, malam)"""

        # 24-hour format
        if hour >= 13:
            return hour

        # Special case for 12
        if hour == 12 and 'malam' in text:
            return 0
        if hour == 12 and 'siang' in text:
            return 12

        # Adjust based on context
        if 'malam' in text:
            if hour >= 6 and hour <= 12:
                return hour + 12
            elif hour >= 1 and hour <= 5:
                return hour
            return 19

        elif 'sore' in text:
            if hour >= 3 and hour <= 6:
                return hour + 12
            return 16

        elif 'siang' in text:
            if hour == 11 or hour == 12:
                return hour
            elif hour >= 1 and hour <= 3:
                return hour + 12
            return 12

        elif 'pagi' in text:
            if hour >= 1 and hour <= 11:
                return hour
            return 8

        return hour
