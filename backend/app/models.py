"""Imports every model so `Base.metadata` is complete for migrations and tests."""
from app.core.db import Base
from app.core.ledger import LedgerEvent
from app.domain.agents import AgentRun, AgentSpecRecord, AgentStep, Lesson
from app.domain.credit import Borrower, Facility
from app.domain.documents import Document, DocumentPage
from app.domain.facts import CalcRun, Fact
from app.domain.funding import FundingEvent
from app.domain.governance import AppSetting, EvalRun, Policy
from app.domain.monitoring import (
    BorrowingBaseReview,
    CovenantTest,
    Cycle,
    CycleStage,
    Job,
    Signal,
    WorkItem,
)
from app.domain.org import User, UserSession
from app.domain.reviews import (
    Action,
    Commentary,
    Package,
    PackageSchedule,
    ReviewMeeting,
    ReviewSheet,
    Snapshot,
)
from app.domain.terms import ReportingObligation, TermsVersion

__all__ = [
    "Action", "AgentRun", "AgentSpecRecord", "AgentStep", "AppSetting", "Base", "Borrower",
    "BorrowingBaseReview", "CalcRun", "Commentary", "CovenantTest", "Cycle", "CycleStage", "Document",
    "DocumentPage", "EvalRun", "Facility", "Fact", "FundingEvent", "Job", "LedgerEvent", "Lesson", "Package",
    "PackageSchedule", "Policy", "ReportingObligation", "ReviewMeeting", "ReviewSheet", "Signal",
    "Snapshot", "TermsVersion", "User", "UserSession", "WorkItem",
]
