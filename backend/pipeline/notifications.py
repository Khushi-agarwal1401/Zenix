"""
Notification System for Zenix AI.
Provides push notifications, alerts, and reminders.
Supports: job alerts, exam reminders, weather warnings, price alerts.
"""

import json
import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class NotificationType(Enum):
    """Types of notifications."""
    JOB_ALERT = "job_alert"
    EXAM_REMINDER = "exam_reminder"
    WEATHER_WARNING = "weather_warning"
    PRICE_ALERT = "price_alert"
    SCHEME_UPDATE = "scheme_update"
    GENERAL = "general"


class NotificationPriority(Enum):
    """Notification priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class Notification:
    """A notification message."""
    id: Optional[int]
    user_id: str
    notification_type: str
    title: str
    message: str
    priority: str
    data: Optional[Dict[str, Any]]
    created_at: str
    read: bool = False
    read_at: Optional[str] = None


@dataclass
class NotificationSubscription:
    """User subscription to notification type."""
    id: Optional[int]
    user_id: str
    notification_type: str
    frequency: str  # "instant", "daily", "weekly"
    filters: Optional[Dict[str, Any]]
    active: bool = True
    created_at: str = ""


class NotificationService:
    """
    Manages notifications for users.
    Stores notifications in SQLite and provides delivery mechanisms.
    """

    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), "..", "data", "notifications.db")
        self.db_path = os.path.realpath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for notifications."""
        conn = sqlite3.connect(self.db_path)
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                notification_type TEXT,
                title TEXT,
                message TEXT,
                priority TEXT,
                data TEXT,
                created_at TEXT,
                read INTEGER DEFAULT 0,
                read_at TEXT
            );
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                notification_type TEXT,
                frequency TEXT,
                filters TEXT,
                active INTEGER DEFAULT 1,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS notification_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_type TEXT,
                title_template TEXT,
                message_template TEXT,
                priority TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_notif_user ON notifications(user_id);
            CREATE INDEX IF NOT EXISTS idx_notif_type ON notifications(notification_type);
            CREATE INDEX IF NOT EXISTS idx_notif_read ON notifications(read);
        """)
        conn.commit()
        self._seed_templates(conn)
        conn.close()

    def _seed_templates(self, conn):
        """Seed notification templates."""
        templates = [
            ("job_alert", "New Government Job: {title}", "A new government job has been posted: {title}. Apply before {deadline}.", "high"),
            ("exam_reminder", "Exam Reminder: {exam_name}", "Your exam {exam_name} is on {date}. Prepare well!", "high"),
            ("weather_warning", "Weather Alert: {city}", "Weather warning for {city}: {warning}. Stay safe!", "urgent"),
            ("price_alert", "Price Alert: {item}", "{item} price has changed to {price}.", "medium"),
            ("scheme_update", "Scheme Update: {scheme_name}", "New update for {scheme_name}: {update}", "medium"),
            ("general", "{title}", "{message}", "low"),
        ]

        for t_type, title, message, priority in templates:
            existing = conn.execute(
                "SELECT id FROM notification_templates WHERE template_type = ? AND title_template = ?",
                (t_type, title),
            ).fetchone()
            if not existing:
                conn.execute(
                    "INSERT INTO notification_templates (template_type, title_template, message_template, priority) VALUES (?, ?, ?, ?)",
                    (t_type, title, message, priority),
                )
        conn.commit()

    def subscribe(self, user_id: str, notification_type: str, frequency: str = "instant",
                  filters: Dict[str, Any] = None) -> int:
        """Subscribe user to a notification type."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()

        cursor = conn.execute(
            """INSERT INTO subscriptions (user_id, notification_type, frequency, filters, active, created_at)
               VALUES (?, ?, ?, ?, 1, ?)""",
            (user_id, notification_type, frequency, json.dumps(filters or {}), now),
        )
        conn.commit()
        sub_id = cursor.lastrowid
        conn.close()

        return sub_id

    def unsubscribe(self, user_id: str, notification_type: str):
        """Unsubscribe user from a notification type."""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE subscriptions SET active = 0 WHERE user_id = ? AND notification_type = ?",
            (user_id, notification_type),
        )
        conn.commit()
        conn.close()

    def send_notification(self, user_id: str, notification_type: str, title: str,
                         message: str, priority: str = "medium",
                         data: Dict[str, Any] = None) -> int:
        """Send a notification to a user."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()

        cursor = conn.execute(
            """INSERT INTO notifications (user_id, notification_type, title, message, priority, data, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, notification_type, title, message, priority, json.dumps(data or {}), now),
        )
        conn.commit()
        notif_id = cursor.lastrowid
        conn.close()

        logger.info(f"Notification sent to {user_id}: {title}")
        return notif_id

    def get_notifications(self, user_id: str, unread_only: bool = False,
                         notification_type: str = None, limit: int = 50) -> List[Notification]:
        """Get notifications for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        query = "SELECT * FROM notifications WHERE user_id = ?"
        params = [user_id]

        if unread_only:
            query += " AND read = 0"
        if notification_type:
            query += " AND notification_type = ?"
            params.append(notification_type)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [
            Notification(
                id=row["id"],
                user_id=row["user_id"],
                notification_type=row["notification_type"],
                title=row["title"],
                message=row["message"],
                priority=row["priority"],
                data=json.loads(row["data"]) if row["data"] else None,
                created_at=row["created_at"],
                read=bool(row["read"]),
                read_at=row["read_at"],
            )
            for row in rows
        ]

    def mark_read(self, notification_id: int):
        """Mark a notification as read."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE notifications SET read = 1, read_at = ? WHERE id = ?",
            (now, notification_id),
        )
        conn.commit()
        conn.close()

    def mark_all_read(self, user_id: str):
        """Mark all notifications as read for a user."""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        conn.execute(
            "UPDATE notifications SET read = 1, read_at = ? WHERE user_id = ? AND read = 0",
            (now, user_id),
        )
        conn.commit()
        conn.close()

    def get_unread_count(self, user_id: str) -> int:
        """Get count of unread notifications."""
        conn = sqlite3.connect(self.db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND read = 0",
            (user_id,),
        ).fetchone()[0]
        conn.close()
        return count

    def get_subscriptions(self, user_id: str) -> List[NotificationSubscription]:
        """Get active subscriptions for a user."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? AND active = 1",
            (user_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        return [
            NotificationSubscription(
                id=row["id"],
                user_id=row["user_id"],
                notification_type=row["notification_type"],
                frequency=row["frequency"],
                filters=json.loads(row["filters"]) if row["filters"] else None,
                active=bool(row["active"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def cleanup_old_notifications(self, days: int = 30):
        """Clean up old read notifications."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "DELETE FROM notifications WHERE read = 1 AND read_at < ?",
            (cutoff,),
        )
        conn.commit()
        conn.close()


class JobAlertService:
    """Service for government job alerts."""

    def __init__(self, notification_service: NotificationService):
        self.notif_service = notification_service

    def create_job_alert(self, user_id: str, job_data: Dict[str, Any]):
        """Create a job alert notification."""
        title = job_data.get("title", "New Government Job")
        deadline = job_data.get("deadline", "Check notification")
        url = job_data.get("url", "")

        message = (
            f"New government job posted!\n\n"
            f"📋 {title}\n"
            f"📅 Deadline: {deadline}\n"
            f"🔗 Apply: {url}\n\n"
            f"Don't miss this opportunity!"
        )

        return self.notif_service.send_notification(
            user_id=user_id,
            notification_type="job_alert",
            title=f"Job Alert: {title}",
            message=message,
            priority="high",
            data=job_data,
        )


class ExamReminderService:
    """Service for exam reminders."""

    def __init__(self, notification_service: NotificationService):
        self.notif_service = notification_service

    def create_exam_reminder(self, user_id: str, exam_data: Dict[str, Any]):
        """Create an exam reminder notification."""
        exam_name = exam_data.get("name", "Exam")
        exam_date = exam_data.get("date", "TBD")
        admit_card = exam_data.get("admit_card_url", "")

        message = (
            f"📚 Exam Reminder!\n\n"
            f"📝 {exam_name}\n"
            f"📅 Date: {exam_date}\n"
        )
        if admit_card:
            message += f"🎫 Admit Card: {admit_card}\n"
        message += "\nAll the best! Prepare well."

        return self.notif_service.send_notification(
            user_id=user_id,
            notification_type="exam_reminder",
            title=f"Exam: {exam_name}",
            message=message,
            priority="high",
            data=exam_data,
        )


class WeatherAlertService:
    """Service for weather warnings."""

    def __init__(self, notification_service: NotificationService):
        self.notif_service = notification_service

    def create_weather_alert(self, user_id: str, weather_data: Dict[str, Any]):
        """Create a weather alert notification."""
        city = weather_data.get("city", "Your area")
        warning = weather_data.get("warning", "Severe weather expected")
        temp = weather_data.get("temperature", "")

        message = (
            f"⛈️ Weather Alert!\n\n"
            f"📍 {city}\n"
            f"⚠️ {warning}\n"
        )
        if temp:
            message += f"🌡️ Temperature: {temp}\n"
        message += "\nStay safe and take precautions!"

        return self.notif_service.send_notification(
            user_id=user_id,
            notification_type="weather_warning",
            title=f"Weather Alert: {city}",
            message=message,
            priority="urgent",
            data=weather_data,
        )


class PriceAlertService:
    """Service for price alerts (gold, petrol, etc.)."""

    def __init__(self, notification_service: NotificationService):
        self.notif_service = notification_service

    def create_price_alert(self, user_id: str, price_data: Dict[str, Any]):
        """Create a price alert notification."""
        item = price_data.get("item", "Item")
        price = price_data.get("price", "N/A")
        change = price_data.get("change", "")

        message = f"💰 Price Alert: {item}\n\nCurrent Price: {price}"
        if change:
            message += f"\nChange: {change}"

        return self.notif_service.send_notification(
            user_id=user_id,
            notification_type="price_alert",
            title=f"Price Alert: {item}",
            message=message,
            priority="medium",
            data=price_data,
        )


# Singleton instances
_notification_service = None
_job_alert_service = None
_exam_reminder_service = None
_weather_alert_service = None
_price_alert_service = None


def get_notification_service() -> NotificationService:
    """Get or create the notification service singleton."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service


def get_job_alert_service() -> JobAlertService:
    """Get or create the job alert service singleton."""
    global _job_alert_service
    if _job_alert_service is None:
        _job_alert_service = JobAlertService(get_notification_service())
    return _job_alert_service


def get_exam_reminder_service() -> ExamReminderService:
    """Get or create the exam reminder service singleton."""
    global _exam_reminder_service
    if _exam_reminder_service is None:
        _exam_reminder_service = ExamReminderService(get_notification_service())
    return _exam_reminder_service


def get_weather_alert_service() -> WeatherAlertService:
    """Get or create the weather alert service singleton."""
    global _weather_alert_service
    if _weather_alert_service is None:
        _weather_alert_service = WeatherAlertService(get_notification_service())
    return _weather_alert_service


def get_price_alert_service() -> PriceAlertService:
    """Get or create the price alert service singleton."""
    global _price_alert_service
    if _price_alert_service is None:
        _price_alert_service = PriceAlertService(get_notification_service())
    return _price_alert_service
