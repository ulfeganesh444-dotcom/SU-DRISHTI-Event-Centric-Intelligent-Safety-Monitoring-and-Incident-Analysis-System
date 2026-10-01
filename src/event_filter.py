"""
Event Filter module for SU-DRISHTI.
Determines whether a detected object/event meets safety criteria and debounces
detections to prevent database flooding (Event Cooldown).
"""

import time
from typing import Dict, List, Set, Optional


class EventFilter:
    """
    Intelligent filter for detected objects and incidents.
    Enforces object whitelisting, confidence thresholds, and cooldown timings.
    """

    DEFAULT_IMPORTANT_OBJECTS: Set[str] = {
        "person",
        "fall",
        "fire",
        "intrusion",
        "dog",
        "cat",
        "car",
        "knife",
        "backpack",
    }

    def __init__(
        self,
        important_objects: Optional[Set[str]] = None,
        min_confidence: float = 0.55,
        default_cooldown: float = 5.0,
        critical_cooldown: float = 3.0,
    ):
        """
        Args:
            important_objects: Set of object labels allowed to trigger events.
            min_confidence: Minimum model confidence threshold (0.0 to 1.0).
            default_cooldown: Seconds to wait before logging the same object category again.
            critical_cooldown: Shorter cooldown for high-priority safety incidents (e.g. fall, fire).
        """
        self.important_objects = (
            important_objects
            if important_objects is not None
            else set(self.DEFAULT_IMPORTANT_OBJECTS)
        )
        self.min_confidence = min_confidence
        self.default_cooldown = default_cooldown
        self.critical_cooldown = critical_cooldown

        # Tracks: {object_name: last_logged_timestamp_float}
        self._last_logged_time: Dict[str, float] = {}

    def is_critical(self, object_name: str) -> bool:
        """Check if an event type is deemed critical safety threat."""
        return object_name.lower() in {"fall", "fire", "knife", "intrusion"}

    def should_log(self, object_name: str, confidence: float) -> bool:
        """
        Evaluates whether an incoming detection should be logged to DB & evidence.

        Args:
            object_name: Name of detected class (e.g. 'person', 'car').
            confidence: Model confidence score (0.0 to 1.0).

        Returns:
            bool: True if event should be recorded, False otherwise.
        """
        normalized_name = object_name.lower().strip()

        # 1. Whitelist Check
        if normalized_name not in self.important_objects:
            return False

        # 2. Confidence Threshold Check
        if confidence < self.min_confidence:
            return False

        # 3. Cooldown / Debounce Check
        current_time = time.time()
        cooldown = (
            self.critical_cooldown
            if self.is_critical(normalized_name)
            else self.default_cooldown
        )

        last_time = self._last_logged_time.get(normalized_name, 0.0)
        time_elapsed = current_time - last_time

        if time_elapsed >= cooldown:
            # Update cooldown timestamp
            self._last_logged_time[normalized_name] = current_time
            return True

        return False

    def reset(self) -> None:
        """Reset internal cooldown state."""
        self._last_logged_time.clear()
