"""
Training Data Pipeline for Zenix AI.

Converts user feedback and interaction logs into structured training examples
for fine-tuning and continuous improvement.

Pipeline:
  1. Load feedback.jsonl (thumbs up/down + request_ids)
  2. Load training_logs.jsonl (query, context, persona, response)
  3. Match feedback to interactions
  4. Generate training examples with quality scores
  5. Export as JSONL for fine-tuning (OpenAI, LLaMA-Factory, etc.)
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class TrainingPipeline:
    """Convert feedback + interaction logs into structured training data."""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        self.data_dir = os.path.realpath(data_dir)
        self.feedback_path = os.path.join(self.data_dir, "feedback.jsonl")
        self.logs_path = os.path.join(self.data_dir, "training_logs.jsonl")
        self.output_dir = os.path.join(self.data_dir, "training")
        os.makedirs(self.output_dir, exist_ok=True)

    def load_feedback(self, days: int = 90) -> Dict[str, str]:
        """Load feedback entries and return {request_id: 'up'/'down'} mapping."""
        if not os.path.exists(self.feedback_path):
            return {}

        cutoff = datetime.now() - timedelta(days=days)
        feedback_map = {}

        with open(self.feedback_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts.replace(tzinfo=None) < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    rid = entry.get("request_id", "")
                    fb = entry.get("feedback", "")
                    if rid and fb in ("up", "down"):
                        feedback_map[rid] = fb
                except json.JSONDecodeError:
                    continue

        return feedback_map

    def load_interactions(self, days: int = 90) -> List[Dict[str, Any]]:
        """Load interaction logs from training_logs.jsonl."""
        if not os.path.exists(self.logs_path):
            return []

        cutoff = datetime.now() - timedelta(days=days)
        interactions = []

        with open(self.logs_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts_str = entry.get("timestamp", "")
                    if ts_str:
                        try:
                            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                            if ts.replace(tzinfo=None) < cutoff:
                                continue
                        except (ValueError, TypeError):
                            pass
                    interactions.append(entry)
                except json.JSONDecodeError:
                    continue

        return interactions

    def generate_training_examples(
        self, days: int = 90, min_quality: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Generate training examples from feedback + interactions.

        Quality scoring:
          - Thumbs up: quality = 1.0
          - Thumbs down: quality = 0.0
          - No feedback: quality = 0.5 (neutral, included but lower weight)
          - Long, detailed responses get slight boost
          - Tool-using responses get slight boost (more useful)

        Returns list of training examples:
        {
            "messages": [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}
            ],
            "quality": 0.0-1.0,
            "metadata": {
                "persona": "desi",
                "tools_used": [...],
                "feedback": "up"/"down"/None,
                "request_id": "..."
            }
        }
        """
        feedback_map = self.load_feedback(days)
        interactions = self.load_interactions(days)

        if not interactions:
            logger.info("No interactions found for training data generation.")
            return []

        examples = []
        for interaction in interactions:
            request_id = interaction.get("request_id", "")
            query = interaction.get("query", "")
            persona = interaction.get("persona", "desi")
            context_docs = interaction.get("retrieved_context", [])

            if not query:
                continue

            # Determine quality from feedback
            feedback = feedback_map.get(request_id)
            if feedback == "up":
                quality = 1.0
            elif feedback == "down":
                quality = 0.0
            else:
                quality = 0.5  # neutral — no feedback given

            # Build the training example
            # System prompt (simplified — real fine-tuning uses the actual system prompt)
            system_content = (
                f"You are Zenix, an AI assistant for India. "
                f"Respond in {'Hinglish, warm and casual' if persona == 'desi' else 'formal English'}. "
                f"Be helpful, accurate, and culturally respectful."
            )

            # User message
            user_content = query

            # Assistant response — we don't have the response in training_logs,
            # so we'll generate a placeholder and flag it
            # In production, you'd log the response too
            assistant_content = interaction.get("response", "")

            if not assistant_content:
                # Skip examples without response
                continue

            # Quality adjustments
            if len(assistant_content) > 200:
                quality = min(1.0, quality + 0.05)  # detailed responses slightly better
            if "tool" in interaction.get("source", "").lower():
                quality = min(1.0, quality + 0.05)  # tool-using responses

            if quality < min_quality:
                continue

            example = {
                "messages": [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content},
                    {"role": "assistant", "content": assistant_content},
                ],
                "quality": round(quality, 2),
                "metadata": {
                    "persona": persona,
                    "context_count": len(context_docs),
                    "feedback": feedback,
                    "request_id": request_id,
                    "timestamp": interaction.get("timestamp", ""),
                },
            }
            examples.append(example)

        # Sort by quality (best first)
        examples.sort(key=lambda x: x["quality"], reverse=True)

        logger.info(
            f"Generated {len(examples)} training examples "
            f"({sum(1 for e in examples if e['quality'] >= 0.8)} high quality)"
        )
        return examples

    def export_jsonl(self, examples: List[Dict], filename: str = None) -> str:
        """Export training examples as JSONL for fine-tuning."""
        if not examples:
            return ""

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"training_data_{timestamp}.jsonl"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for example in examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")

        logger.info(f"Exported {len(examples)} examples to {filepath}")
        return filepath

    def export_openai_format(self, examples: List[Dict], filename: str = None) -> str:
        """Export in OpenAI fine-tuning format."""
        if not examples:
            return ""

        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"openai_finetune_{timestamp}.jsonl"

        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            for example in examples:
                # OpenAI format: {"messages": [...]}
                openai_example = {
                    "messages": example["messages"]
                }
                f.write(json.dumps(openai_example, ensure_ascii=False) + "\n")

        logger.info(f"Exported OpenAI format: {len(examples)} examples to {filepath}")
        return filepath

    def export_preference_pairs(self, examples: List[Dict], filename: str = None) -> List[Dict]:
        """
        Generate preference pairs for DPO/RHLF training.
        Pairs a thumbs-up example with a thumbs-down example on similar queries.
        """
        positive = [e for e in examples if e["quality"] >= 0.8]
        negative = [e for e in examples if e["quality"] <= 0.2]

        if not positive or not negative:
            return []

        pairs = []
        used_negatives = set()

        for pos in positive:
            pos_query = pos["messages"][1]["content"].lower()
            # Find a negative example with somewhat similar query
            best_neg = None
            best_score = 0
            for i, neg in enumerate(negative):
                if i in used_negatives:
                    continue
                neg_query = neg["messages"][1]["content"].lower()
                # Simple word overlap similarity
                pos_words = set(pos_query.split())
                neg_words = set(neg_query.split())
                overlap = len(pos_words & neg_words) / max(len(pos_words | neg_words), 1)
                if overlap > best_score:
                    best_score = overlap
                    best_neg = (i, neg)

            if best_neg and best_score > 0.2:
                idx, neg = best_neg
                used_negatives.add(idx)
                pairs.append({
                    "chosen": pos["messages"][2]["content"],
                    "rejected": neg["messages"][2]["content"],
                    "prompt": pos["messages"][1]["content"],
                    "system": pos["messages"][0]["content"],
                })

        if filename and pairs:
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                for pair in pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")
            logger.info(f"Exported {len(pairs)} preference pairs to {filepath}")

        return pairs

    def generate_report(self, days: int = 30) -> str:
        """Generate a human-readable training data report."""
        examples = self.generate_training_examples(days)

        if not examples:
            return (
                "=" * 60 + "\n"
                "TRAINING DATA REPORT\n"
                "=" * 60 + "\n"
                "No training data available. Start collecting user feedback.\n"
                "=" * 60
            )

        total = len(examples)
        high_quality = sum(1 for e in examples if e["quality"] >= 0.8)
        low_quality = sum(1 for e in examples if e["quality"] <= 0.2)
        neutral = total - high_quality - low_quality
        personas = defaultdict(int)
        for e in examples:
            personas[e["metadata"]["persona"]] += 1

        lines = [
            "=" * 60,
            "TRAINING DATA REPORT",
            "=" * 60,
            f"Period: Last {days} days",
            f"Total Examples: {total}",
            f"",
            f"Quality Distribution:",
            f"  High Quality (thumbs up):  {high_quality} ({high_quality/total*100:.0f}%)",
            f"  Neutral (no feedback):     {neutral} ({neutral/total*100:.0f}%)",
            f"  Low Quality (thumbs down): {low_quality} ({low_quality/total*100:.0f}%)",
            f"",
            f"Persona Breakdown:",
        ]
        for persona, count in sorted(personas.items(), key=lambda x: -x[1]):
            lines.append(f"  {persona}: {count} examples")

        lines.extend([
            f"",
            f"Output Directory: {self.output_dir}",
            f"",
            f"To generate training data:",
            f"  from pipeline.training_pipeline import training_pipeline",
            f"  examples = training_pipeline.generate_training_examples()",
            f"  training_pipeline.export_jsonl(examples)",
            f"  training_pipeline.export_openai_format(examples)",
            "=" * 60,
        ])

        return "\n".join(lines)


# Singleton
training_pipeline = TrainingPipeline()
