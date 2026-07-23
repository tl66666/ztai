"""Application modules exposed to HTTP adapters."""

from .container import ApplicationContainer
from .interviews import InterviewModule
from .opportunities import OpportunityModule
from .resumes import ResumeModule

__all__ = [
    "ApplicationContainer",
    "InterviewModule",
    "OpportunityModule",
    "ResumeModule",
]
