"""
Budget & Expense Tracker Module for Zenix AI.
Provides personal finance management: expense tracking, budgeting, and analysis.
"""

import json
import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Transaction:
    """A financial transaction."""
    id: Optional[int]
    user_id: str
    amount: float
    category: str
    description: str
    transaction_type: str  # "income" or "expense"
    date: str
    payment_method: str
    tags: Optional[List[str]] = None


@dataclass
class Budget:
    """Budget for a category."""
    id: Optional[int]
    user_id: str
    category: str
    monthly_limit: float
    spent: float
    remaining: float
    percentage_used: float


class BudgetTracker:
    """
    Personal finance tracker for expenses and income.
    """

    # Default categories
    DEFAULT_EXPENSE_CATEGORIES = [
        "Food & Dining", "Transportation", "Shopping", "Bills & Utilities",
        "Entertainment", "Health & Medical", "Education", "Travel",
        "Groceries", "Rent", "Insurance", "Savings", "Other"
    ]

    DEFAULT_INCOME_CATEGORIES = [
        "Salary", "Business", "Freelance", "Investment", "Gift", "Other"
    ]

    # Common Indian payment methods
    PAYMENT_METHODS = [
        "Cash", "UPI", "Credit Card", "Debit Card", "Net Banking",
        "Wallet", "Cheque", "NEFT", "RTGS", "IMPS"
    ]

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "budget_tracker.db")
        self.db_path = os.path.realpath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                amount REAL,
                category TEXT,
                description TEXT,
                transaction_type TEXT,
                date TEXT,
                payment_method TEXT,
                tags TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                category TEXT,
                monthly_limit REAL,
                month TEXT,
                UNIQUE(user_id, category, month)
            );
            CREATE TABLE IF NOT EXISTS savings_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                goal_name TEXT,
                target_amount REAL,
                current_amount REAL,
                deadline TEXT,
                created_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_trans_user ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_trans_date ON transactions(date);
            CREATE INDEX IF NOT EXISTS idx_trans_category ON transactions(category);
        """)
        conn.commit()
        conn.close()

    def add_transaction(self, user_id: str, amount: float, category: str,
                       description: str, transaction_type: str = "expense",
                       date: str = None, payment_method: str = "UPI",
                       tags: List[str] = None) -> int:
        """
        Add a transaction.

        Args:
            user_id: User identifier
            amount: Transaction amount
            category: Category (e.g., "Food & Dining")
            description: Transaction description
            transaction_type: "income" or "expense"
            date: Transaction date (YYYY-MM-DD), defaults to today
            payment_method: Payment method
            tags: Optional tags

        Returns:
            Transaction ID
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """INSERT INTO transactions 
               (user_id, amount, category, description, transaction_type, date, payment_method, tags, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, amount, category, description, transaction_type,
             date, payment_method, json.dumps(tags or []), datetime.now().isoformat()),
        )
        conn.commit()
        trans_id = cursor.lastrowid
        conn.close()

        return trans_id

    def get_transactions(self, user_id: str, start_date: str = None,
                        end_date: str = None, category: str = None,
                        transaction_type: str = None, limit: int = 100) -> List[Transaction]:
        """Get transactions for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM transactions WHERE user_id = ?"
        params = [user_id]

        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if category:
            query += " AND category = ?"
            params.append(category)
        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)

        query += " ORDER BY date DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Transaction(
                id=row["id"],
                user_id=row["user_id"],
                amount=row["amount"],
                category=row["category"],
                description=row["description"],
                transaction_type=row["transaction_type"],
                date=row["date"],
                payment_method=row["payment_method"],
                tags=json.loads(row["tags"]) if row["tags"] else [],
            )
            for row in rows
        ]

    def set_budget(self, user_id: str, category: str, monthly_limit: float,
                  month: str = None) -> int:
        """Set monthly budget for a category."""
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """INSERT OR REPLACE INTO budgets (user_id, category, monthly_limit, month)
               VALUES (?, ?, ?, ?)""",
            (user_id, category, monthly_limit, month),
        )
        conn.commit()
        budget_id = cursor.lastrowid
        conn.close()

        return budget_id

    def get_budgets(self, user_id: str, month: str = None) -> List[Budget]:
        """Get budgets for a user."""
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM budgets WHERE user_id = ? AND month = ?",
            (user_id, month),
        )
        rows = cursor.fetchall()
        conn.close()

        budgets = []
        for row in rows:
            # Calculate spent amount
            spent = self._get_category_spent(user_id, row["category"], month)
            remaining = row["monthly_limit"] - spent
            percentage = (spent / row["monthly_limit"] * 100) if row["monthly_limit"] > 0 else 0

            budgets.append(Budget(
                id=row["id"],
                user_id=row["user_id"],
                category=row["category"],
                monthly_limit=row["monthly_limit"],
                spent=spent,
                remaining=remaining,
                percentage_used=round(percentage, 2),
            ))

        return budgets

    def get_monthly_summary(self, user_id: str, month: str = None) -> Dict[str, Any]:
        """Get monthly financial summary."""
        if month is None:
            month = datetime.now().strftime("%Y-%m")

        start_date = f"{month}-01"
        end_date = f"{month}-31"

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Total income
        income = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total 
               FROM transactions WHERE user_id = ? AND transaction_type = 'income' 
               AND date >= ? AND date <= ?""",
            (user_id, start_date, end_date),
        ).fetchone()["total"]

        # Total expenses
        expenses = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total 
               FROM transactions WHERE user_id = ? AND transaction_type = 'expense' 
               AND date >= ? AND date <= ?""",
            (user_id, start_date, end_date),
        ).fetchone()["total"]

        # Category-wise expenses
        category_expenses = conn.execute(
            """SELECT category, SUM(amount) as total 
               FROM transactions WHERE user_id = ? AND transaction_type = 'expense' 
               AND date >= ? AND date <= ?
               GROUP BY category ORDER BY total DESC""",
            (user_id, start_date, end_date),
        ).fetchall()

        conn.close()

        savings = income - expenses

        return {
            "month": month,
            "total_income": round(income, 2),
            "total_expenses": round(expenses, 2),
            "savings": round(savings, 2),
            "savings_rate": round((savings / income * 100) if income > 0 else 0, 2),
            "category_breakdown": {
                row["category"]: round(row["total"], 2)
                for row in category_expenses
            },
            "transaction_count": len(category_expenses),
        }

    def get_category_analysis(self, user_id: str, months: int = 3) -> Dict[str, Any]:
        """Get category-wise spending analysis over multiple months."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=months * 30)).strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        cursor = conn.execute(
            """SELECT category, 
                      SUM(amount) as total,
                      COUNT(*) as count,
                      AVG(amount) as avg_per_transaction
               FROM transactions 
               WHERE user_id = ? AND transaction_type = 'expense' 
               AND date >= ? AND date <= ?
               GROUP BY category 
               ORDER BY total DESC""",
            (user_id, start_date, end_date),
        )
        rows = cursor.fetchall()
        conn.close()

        total_expenses = sum(row["total"] for row in rows)

        return {
            "period_months": months,
            "total_expenses": round(total_expenses, 2),
            "categories": [
                {
                    "category": row["category"],
                    "total": round(row["total"], 2),
                    "count": row["count"],
                    "average": round(row["avg_per_transaction"], 2),
                    "percentage": round(row["total"] / total_expenses * 100, 2) if total_expenses > 0 else 0,
                }
                for row in rows
            ],
        }

    def add_savings_goal(self, user_id: str, goal_name: str,
                        target_amount: float, deadline: str = None) -> int:
        """Add a savings goal."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            """INSERT INTO savings_goals 
               (user_id, goal_name, target_amount, current_amount, deadline, created_at)
               VALUES (?, ?, ?, 0, ?, ?)""",
            (user_id, goal_name, target_amount, deadline, datetime.now().isoformat()),
        )
        conn.commit()
        goal_id = cursor.lastrowid
        conn.close()

        return goal_id

    def update_savings_goal(self, goal_id: int, amount: float):
        """Update savings goal progress."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE savings_goals SET current_amount = current_amount + ? WHERE id = ?",
            (amount, goal_id),
        )
        conn.commit()
        conn.close()

    def get_savings_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all savings goals for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM savings_goals WHERE user_id = ? ORDER BY deadline",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            {
                "id": row["id"],
                "goal_name": row["goal_name"],
                "target_amount": row["target_amount"],
                "current_amount": row["current_amount"],
                "deadline": row["deadline"],
                "progress_percentage": round(
                    row["current_amount"] / row["target_amount"] * 100, 2
                ) if row["target_amount"] > 0 else 0,
                "remaining": row["target_amount"] - row["current_amount"],
            }
            for row in rows
        ]

    def _get_category_spent(self, user_id: str, category: str, month: str) -> float:
        """Get total spent in a category for a month."""
        conn = sqlite3.connect(self.db_path)
        result = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) as total 
               FROM transactions 
               WHERE user_id = ? AND category = ? AND transaction_type = 'expense'
               AND date >= ? AND date <= ?""",
            (user_id, category, f"{month}-01", f"{month}-31"),
        ).fetchone()[0]
        conn.close()
        return result

    def get_quick_stats(self, user_id: str) -> Dict[str, Any]:
        """Get quick financial stats."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        conn = sqlite3.connect(self.db_path)

        # Today's expenses
        today_expenses = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM transactions 
               WHERE user_id = ? AND transaction_type = 'expense' AND date = ?""",
            (user_id, today),
        ).fetchone()[0]

        # This month's expenses
        month_expenses = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM transactions 
               WHERE user_id = ? AND transaction_type = 'expense' 
               AND date >= ? AND date <= ?""",
            (user_id, f"{month}-01", f"{month}-31"),
        ).fetchone()[0]

        # This month's income
        month_income = conn.execute(
            """SELECT COALESCE(SUM(amount), 0) FROM transactions 
               WHERE user_id = ? AND transaction_type = 'income' 
               AND date >= ? AND date <= ?""",
            (user_id, f"{month}-01", f"{month}-31"),
        ).fetchone()[0]

        # Transaction count
        total_transactions = conn.execute(
            "SELECT COUNT(*) FROM transactions WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]

        conn.close()

        return {
            "today_expenses": round(today_expenses, 2),
            "month_expenses": round(month_expenses, 2),
            "month_income": round(month_income, 2),
            "month_savings": round(month_income - month_expenses, 2),
            "total_transactions": total_transactions,
        }


# Singleton instance
_budget_tracker = None


def get_budget_tracker() -> BudgetTracker:
    """Get or create the budget tracker singleton."""
    global _budget_tracker
    if _budget_tracker is None:
        _budget_tracker = BudgetTracker()
    return _budget_tracker
