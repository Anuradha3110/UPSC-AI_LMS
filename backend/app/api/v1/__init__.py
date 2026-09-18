from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    answers,
    auth,
    billing,
    cms,
    content,
    doubts,
    interview,
    mentor,
    notifications,
    revision,
    study,
    syllabus,
    tests,
)

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(syllabus.router, prefix="/syllabus", tags=["syllabus"])
router.include_router(content.router, prefix="/content", tags=["content"])
router.include_router(tests.router, prefix="/tests", tags=["tests"])
router.include_router(answers.router, prefix="/answers", tags=["answers"])
router.include_router(revision.router, prefix="/revision", tags=["revision"])
router.include_router(doubts.router, prefix="/doubts", tags=["doubts"])
router.include_router(mentor.router, prefix="/mentor", tags=["mentor"])
router.include_router(interview.router, prefix="/interview", tags=["interview"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(cms.router, prefix="/cms", tags=["cms"])
router.include_router(billing.router, prefix="/billing", tags=["billing"])
router.include_router(study.router, prefix="/study", tags=["study"])
