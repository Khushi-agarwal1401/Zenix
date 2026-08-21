"""
Document Comparison Module for Zenix AI.
Provides diff analysis between two documents or texts.
Supports: text comparison, document diff, contract comparison.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher, unified_diff, context_diff

logger = logging.getLogger(__name__)


@dataclass
class DiffResult:
    """Result of document comparison."""
    success: bool
    summary: Dict[str, Any]
    differences: List[Dict[str, Any]]
    similarity_score: float  # 0-100%
    diff_text: str
    error: Optional[str] = None


@dataclass
class DiffLine:
    """A single line difference."""
    line_number: int
    old_line: Optional[int]
    new_line: Optional[int]
    content: str
    change_type: str  # "added", "removed", "unchanged", "modified"


class DocumentComparator:
    """
    Compare two documents or texts and find differences.
    """

    def __init__(self):
        pass

    def compare_texts(self, text1: str, text2: str,
                     label1: str = "Document 1",
                     label2: str = "Document 2") -> DiffResult:
        """
        Compare two texts and find differences.

        Args:
            text1: First text
            text2: Second text
            label1: Label for first document
            label2: Label for second document

        Returns:
            DiffResult with differences and similarity score
        """
        try:
            # Calculate similarity score
            similarity = self._calculate_similarity(text1, text2)

            # Get line-by-line diff
            lines1 = text1.splitlines(keepends=True)
            lines2 = text2.splitlines(keepends=True)

            # Generate unified diff
            diff_lines = list(unified_diff(
                lines1, lines2,
                fromfile=label1,
                tofile=label2,
                lineterm=''
            ))

            # Parse differences
            differences = self._parse_diff(diff_lines)

            # Generate summary
            summary = self._generate_summary(lines1, lines2, differences, similarity)

            # Generate readable diff text
            diff_text = self._format_diff(diff_lines)

            return DiffResult(
                success=True,
                summary=summary,
                differences=differences,
                similarity_score=similarity,
                diff_text=diff_text,
            )

        except Exception as e:
            return DiffResult(
                success=False,
                summary={},
                differences=[],
                similarity_score=0,
                diff_text="",
                error=f"Comparison failed: {str(e)}"
            )

    def compare_files(self, file1_path: str, file2_path: str) -> DiffResult:
        """
        Compare two files.

        Args:
            file1_path: Path to first file
            file2_path: Path to second file

        Returns:
            DiffResult with differences
        """
        try:
            with open(file1_path, 'r', encoding='utf-8', errors='replace') as f:
                text1 = f.read()
            with open(file2_path, 'r', encoding='utf-8', errors='replace') as f:
                text2 = f.read()

            label1 = os.path.basename(file1_path)
            label2 = os.path.basename(file2_path)

            return self.compare_texts(text1, text2, label1, label2)

        except FileNotFoundError as e:
            return DiffResult(
                success=False,
                summary={},
                differences=[],
                similarity_score=0,
                diff_text="",
                error=f"File not found: {str(e)}"
            )
        except Exception as e:
            return DiffResult(
                success=False,
                summary={},
                differences=[],
                similarity_score=0,
                diff_text="",
                error=f"File comparison failed: {str(e)}"
            )

    def compare_contracts(self, text1: str, text2: str) -> DiffResult:
        """
        Compare two contracts with clause-level analysis.

        Args:
            text1: First contract text
            text2: Second contract text

        Returns:
            DiffResult with clause-level differences
        """
        # Split by clauses (assuming numbered clauses or paragraphs)
        clauses1 = self._extract_clauses(text1)
        clauses2 = self._extract_clauses(text2)

        # Compare clauses
        differences = []
        for i, (c1, c2) in enumerate(zip(clauses1, clauses2)):
            if c1 != c2:
                similarity = self._calculate_similarity(c1, c2)
                differences.append({
                    "clause_number": i + 1,
                    "type": "modified" if similarity > 50 else "different",
                    "old": c1[:500],
                    "new": c2[:500],
                    "similarity": similarity,
                })

        # Check for extra clauses
        if len(clauses1) > len(clauses2):
            for i in range(len(clauses2), len(clauses1)):
                differences.append({
                    "clause_number": i + 1,
                    "type": "removed",
                    "old": clauses1[i][:500],
                    "new": "",
                    "similarity": 0,
                })
        elif len(clauses2) > len(clauses1):
            for i in range(len(clauses1), len(clauses2)):
                differences.append({
                    "clause_number": i + 1,
                    "type": "added",
                    "old": "",
                    "new": clauses2[i][:500],
                    "similarity": 0,
                })

        similarity = self._calculate_similarity(text1, text2)

        summary = {
            "total_clauses": max(len(clauses1), len(clauses2)),
            "modified_clauses": sum(1 for d in differences if d["type"] == "modified"),
            "added_clauses": sum(1 for d in differences if d["type"] == "added"),
            "removed_clauses": sum(1 for d in differences if d["type"] == "removed"),
            "similarity_score": similarity,
        }

        return DiffResult(
            success=True,
            summary=summary,
            differences=differences,
            similarity_score=similarity,
            diff_text=self._format_contract_diff(differences),
        )

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity score between two texts (0-100)."""
        return round(SequenceMatcher(None, text1, text2).ratio() * 100, 2)

    def _parse_diff(self, diff_lines: List[str]) -> List[Dict[str, Any]]:
        """Parse unified diff lines into structured differences."""
        differences = []
        old_line = 0
        new_line = 0

        for line in diff_lines:
            if line.startswith('---') or line.startswith('+++') or line.startswith('@@'):
                # Extract line numbers from @@ header
                if line.startswith('@@'):
                    match = re.search(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
                    if match:
                        old_line = int(match.group(1))
                        new_line = int(match.group(2))
                continue

            if line.startswith('-'):
                differences.append({
                    "old_line": old_line,
                    "new_line": None,
                    "content": line[1:],
                    "type": "removed",
                })
                old_line += 1
            elif line.startswith('+'):
                differences.append({
                    "old_line": None,
                    "new_line": new_line,
                    "content": line[1:],
                    "type": "added",
                })
                new_line += 1
            elif line.startswith(' '):
                differences.append({
                    "old_line": old_line,
                    "new_line": new_line,
                    "content": line[1:] if len(line) > 1 else "",
                    "type": "unchanged",
                })
                old_line += 1
                new_line += 1

        return differences

    def _generate_summary(self, lines1: List[str], lines2: List[str],
                         differences: List[Dict], similarity: float) -> Dict[str, Any]:
        """Generate comparison summary."""
        added = sum(1 for d in differences if d["type"] == "added")
        removed = sum(1 for d in differences if d["type"] == "removed")
        unchanged = sum(1 for d in differences if d["type"] == "unchanged")

        return {
            "original_lines": len(lines1),
            "modified_lines": len(lines2),
            "lines_added": added,
            "lines_removed": removed,
            "lines_unchanged": unchanged,
            "similarity_score": similarity,
            "change_percentage": round(100 - similarity, 2),
        }

    def _format_diff(self, diff_lines: List[str]) -> str:
        """Format diff lines into readable text."""
        return ''.join(diff_lines)

    def _extract_clauses(self, text: str) -> List[str]:
        """Extract clauses from a contract document."""
        # Try to split by numbered clauses
        clause_pattern = r'(?:^|\n)\s*(?:\d+\.|\([a-z]\)|[A-Z]\.)\s*'
        clauses = re.split(clause_pattern, text)
        clauses = [c.strip() for c in clauses if c.strip()]

        # If no numbered clauses found, split by paragraphs
        if len(clauses) <= 1:
            clauses = [p.strip() for p in text.split('\n\n') if p.strip()]

        return clauses

    def _format_contract_diff(self, differences: List[Dict]) -> str:
        """Format contract differences into readable text."""
        lines = ["**Contract Comparison Results:**\n"]

        for diff in differences:
            clause_num = diff["clause_number"]
            change_type = diff["type"].upper()

            lines.append(f"\n**Clause {clause_num} - {change_type}:**")

            if diff.get("old"):
                lines.append(f"  Original: {diff['old'][:200]}...")
            if diff.get("new"):
                lines.append(f"  Modified: {diff['new'][:200]}...")
            if diff.get("similarity"):
                lines.append(f"  Similarity: {diff['similarity']}%")

        return '\n'.join(lines)

    def get_quick_diff(self, text1: str, text2: str) -> str:
        """Get a quick summary of differences."""
        similarity = self._calculate_similarity(text1, text2)

        lines1 = set(text1.splitlines())
        lines2 = set(text2.splitlines())

        added = lines2 - lines1
        removed = lines1 - lines2

        result = [
            f"**Quick Diff Summary:**",
            f"Similarity: {similarity}%",
            f"Lines added: {len(added)}",
            f"Lines removed: {len(removed)}",
        ]

        if added:
            result.append("\n**Added:**")
            for line in list(added)[:5]:
                result.append(f"  + {line[:100]}")

        if removed:
            result.append("\n**Removed:**")
            for line in list(removed)[:5]:
                result.append(f"  - {line[:100]}")

        return '\n'.join(result)


# Singleton instance
_document_comparator = None


def get_document_comparator() -> DocumentComparator:
    """Get or create the document comparator singleton."""
    global _document_comparator
    if _document_comparator is None:
        _document_comparator = DocumentComparator()
    return _document_comparator
