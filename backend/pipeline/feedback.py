"""
Feedback Loop Module for Zenix AI.
Analyzes feedback.jsonl, tracks thumbs-down responses, and generates improvement reports.
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import Counter


class FeedbackAnalyzer:
    """Analyze user feedback to identify improvement opportunities."""

    def __init__(self, feedback_path: str = None):
        if feedback_path is None:
            feedback_path = os.path.join(
                os.path.dirname(__file__), "..", "data", "feedback.jsonl"
            )
        self.feedback_path = os.path.realpath(feedback_path)

    def load_feedback(self, days: int = 30) -> List[Dict]:
        """Load feedback from the last N days."""
        if not os.path.exists(self.feedback_path):
            return []

        cutoff = datetime.now() - timedelta(days=days)
        entries = []

        with open(self.feedback_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    # Parse timestamp
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts.replace(tzinfo=None) >= cutoff:
                                entries.append(entry)
                        except (ValueError, TypeError):
                            entries.append(entry)  # Include if can't parse date
                    else:
                        entries.append(entry)
                except json.JSONDecodeError:
                    continue

        return entries

    def analyze(self, days: int = 30) -> Dict[str, Any]:
        """
        Analyze feedback and return comprehensive report.

        Returns:
            Dict with overall stats, thumbs breakdown, and improvement suggestions.
        """
        entries = self.load_feedback(days)

        if not entries:
            return {
                "total_feedback": 0,
                "message": "No feedback data available yet.",
                "summary": "Start collecting user feedback to get improvement insights.",
            }

        # Count thumbs up/down
        thumbs_up = sum(1 for e in entries if e.get("feedback") == "up")
        thumbs_down = sum(1 for e in entries if e.get("feedback") == "down")
        total = thumbs_up + thumbs_down

        # Calculate satisfaction rate
        satisfaction_rate = (thumbs_up / total * 100) if total > 0 else 0

        # Get thumbs down request IDs for follow-up
        thumbs_down_ids = [
            e.get("request_id") for e in entries if e.get("feedback") == "down"
        ]

        # Find most recent thumbs down (for improvement suggestions)
        recent_downs = [
            e for e in entries if e.get("feedback") == "down"
        ][-10:]  # Last 10

        # Generate improvement suggestions
        suggestions = self._generate_suggestions(entries)

        return {
            "total_feedback": total,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_rate": f"{satisfaction_rate:.1f}%",
            "thumbs_down_ids": thumbs_down_ids[-5:],  # Last 5
            "recent_negative_feedback": recent_downs,
            "suggestions": suggestions,
            "analysis_period_days": days,
        }

    def _generate_suggestions(self, entries: List[Dict]) -> List[str]:
        """Generate improvement suggestions based on feedback patterns."""
        suggestions = []

        thumbs_down = [e for e in entries if e.get("feedback") == "down"]
        thumbs_up = [e for e in entries if e.get("feedback") == "up"]

        total = len(thumbs_down) + len(thumbs_up)
        if total == 0:
            return ["Collect more feedback to get suggestions."]

        down_rate = len(thumbs_down) / total

        if down_rate > 0.3:
            suggestions.append(
                "High negative feedback rate detected. Review recent responses for accuracy and tone."
            )

        if len(thumbs_down) > 5:
            suggestions.append(
                f"{len(thumbs_down)} negative responses found. Consider reviewing the system prompt and tool outputs."
            )

        if len(entries) < 10:
            suggestions.append(
                "Collect more feedback (10+ responses) for meaningful insights."
            )

        if down_rate < 0.1 and total > 20:
            suggestions.append(
                "Excellent satisfaction rate! Consider expanding knowledge base for new topics."
            )

        return suggestions or ["Feedback patterns look healthy. Keep improving!"]

    def get_improvement_report(self) -> str:
        """Generate a human-readable improvement report."""
        analysis = self.analyze(days=7)

        lines = [
            "=" * 60,
            "ZENIX FEEDBACK IMPROVEMENT REPORT",
            "=" * 60,
            f"Period: Last 7 days",
            f"Total Feedback: {analysis['total_feedback']}",
            f"Thumbs Up: {analysis.get('thumbs_up', 0)}",
            f"Thumbs Down: {analysis.get('thumbs_down', 0)}",
            f"Satisfaction Rate: {analysis.get('satisfaction_rate', 'N/A')}",
            "",
            "IMPROVEMENT SUGGESTIONS:",
        ]

        for i, suggestion in enumerate(analysis.get("suggestions", []), 1):
            lines.append(f"  {i}. {suggestion}")

        lines.append("=" * 60)

        return "\n".join(lines)

    def log_feedback(self, request_id: str, feedback: str) -> bool:
        """Log a new feedback entry."""
        try:
            os.makedirs(os.path.dirname(self.feedback_path), exist_ok=True)

            entry = {
                "timestamp": datetime.now().isoformat(),
                "request_id": request_id,
                "feedback": feedback,  # "up" or "down"
            }

            with open(self.feedback_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")

            return True
        except Exception as e:
            print(f"Failed to log feedback: {e}")
            return False


# Singleton
feedback_analyzer = FeedbackAnalyzer()
