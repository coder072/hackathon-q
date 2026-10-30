"""RST-001 이진 판정."""

from app.analyzer.checks import CheckCode
from app.schemas.analysis import CheckResult, Verdict

MAX_SCORE = 10
SAFE_MAX_SCORE = 3


def decide(checks: list[CheckResult]) -> tuple[int, Verdict]:
    if any(c.detected and c.code == CheckCode.BLOCKLIST_MATCH for c in checks):
        return MAX_SCORE, Verdict.SUSPICIOUS

    score = min(sum(c.score for c in checks if c.detected), MAX_SCORE)
    verdict = Verdict.SAFE if score <= SAFE_MAX_SCORE else Verdict.SUSPICIOUS
    return score, verdict
