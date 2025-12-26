"""
Indonesian AI Reminder - Source Package
"""

__version__ = "2.0.0"
__author__ = "Abdul Azizur Rokhman"
__description__ = "Voice-Enabled AI Reminder with Indonesian NER"

from .ner_model import ReminderNERModel
from .time_normalizer import TimeNormalizer

__all__ = ["ReminderNERModel", "TimeNormalizer"]
