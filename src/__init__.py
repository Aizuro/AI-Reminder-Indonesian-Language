"""
Indonesian AI Reminder - Source Package
"""

__version__ = "2.1.0"
__author__ = "Abdul Azizur Rokhman"
__description__ = "Voice-Enabled AI Reminder with Indonesian NER"

__all__ = ["ReminderNERModel", "TimeNormalizer", "build_ics"]


def __getattr__(name):
    # Lazy import agar modul ringan (TimeNormalizer, ics_export) bisa dipakai
    # dan diuji tanpa memuat torch/transformers.
    if name == "ReminderNERModel":
        from .ner_model import ReminderNERModel
        return ReminderNERModel
    if name == "TimeNormalizer":
        from .time_normalizer import TimeNormalizer
        return TimeNormalizer
    if name == "build_ics":
        from .ics_export import build_ics
        return build_ics
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
