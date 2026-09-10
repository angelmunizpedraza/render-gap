"""render-gap — what your page shows a browser but hides from an AI crawler.

Most citation crawlers (GPTBot, OAI-SearchBot, PerplexityBot, Claude-SearchBot,
Google-Extended) do not execute JavaScript. render-gap compares the raw HTML a
server returns with the DOM a browser ends up with, and reports exactly which
content only exists after JavaScript has run.
"""

from .extract import Snapshot, extract
from .diff import Gap, GapReport, compare
from .score import score_report

__all__ = ["Snapshot", "extract", "Gap", "GapReport", "compare", "score_report"]
__version__ = "0.1.0"
