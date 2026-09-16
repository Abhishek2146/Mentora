# Study Streak Service

import re
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.logger import get_logger
from app.models.study_streak import UserStreak, DailyStudySummary
from app.models.user import User
from app.models.progress import Progress
from app.models.quiz import QuizAttempt
from app.schemas.study_streak import (
    StudyStreakOut,
    DailyStudySummaryOut,
    StudyActivitySummary,
)


logger = get_logger(__name__)


MINIMUM_STUDY_MINUTES = 30  # Default minimum qualifying study time


class StudyStreakService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_streak(self, user_id: int) -> StudyStreakOut:
        """Get the user's current study streak."""
        # Get or create user streak record
        result = await self.db.execute(
            select(UserStreak).where(UserStreak.user_id == user_id)
        )
        streak = result.scalars().first()

        if not streak:
            streak = UserStreak(user_id=user_id)
            self.db.add(streak)
            await self.db.flush()
            await self.db.commit()

        return StudyStreakOut(
            id=streak.id,
            user_id=streak.user_id,
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            total_study_days=streak.total_study_days,
            total_study_minutes=streak.total_study_minutes,
            last_qualifying_date=streak.last_qualifying_date,
        )

    async def recalculate_streak(self, user_id: int) -> StudyStreakOut:
        """Recalculate the user's streak based on daily study summaries."""
        streak = await self.get_streak(user_id)

        # Get all qualifying days (days with >= minimum study minutes)
        # Group by date and study_minutes
        result = await self.db.execute(
            select(
                DailyStudySummary.date,
                DailyStudySummary.study_minutes,
                DailyStudySummary.qualifying,
            )
            .where(DailyStudySummary.user_id == user_id)
            .order_by(DailyStudySummary.date.asc())
        )
        days = result.fetchall()

        if not days:
            streak.current_streak = 0
            streak.longest_streak = 0
            streak.total_study_days = 0
            streak.total_study_minutes = 0
            streak.last_qualifying_date = None
            await self.db.flush()
            await self.db.commit()
            return StudyStreakOut(
                id=streak.id,
                user_id=streak.user_id,
                current_streak=0,
                longest_streak=0,
                total_study_days=0,
                total_study_minutes=0,
                last_qualifying_date=None,
            )

        # Calculate streaks
        # A day qualifies if qualifying=True (which means study_minutes >= MINIMUM_STUDY_MINUTES)
        qualifying_dates = []
        total_minutes = 0

        for row in days:
            date_str = row.date
            study_minutes = row.study_minutes
            is_qualifying = row.qualifying

            if is_qualifying:
                total_minutes += study_minutes
                qualifying_dates.append(date_str)

        # Calculate current streak (most recent consecutive qualifying days from today)
        current_streak = await self._calculate_current_streak(qualifying_dates)

        # Calculate longest streak
        longest_streak = await self._calculate_longest_streak(qualifying_dates)

        # Total study days
        total_study_days = len(qualifying_dates)

        # Last qualifying date
        last_qualifying_date = qualifying_dates[-1] if qualifying_dates else None

        # Update streak record
        streak.current_streak = current_streak
        streak.longest_streak = longest_streak
        streak.total_study_days = total_study_days
        streak.total_study_minutes = total_minutes
        streak.last_qualifying_date = (
            datetime.fromisoformat(last_qualifying_date).replace(tzinfo=None)
            if last_qualifying_date
            else None
        )

        await self.db.flush()
        await self.db.commit()

        return StudyStreakOut(
            id=streak.id,
            user_id=streak.user_id,
            current_streak=streak.current_streak,
            longest_streak=streak.longest_streak,
            total_study_days=streak.total_study_days,
            total_study_minutes=streak.total_study_minutes,
            last_qualifying_date=streak.last_qualifying_date,
        )

    async def _calculate_current_streak(self, qualifying_dates: List[str]) -> int:
        """Calculate the current streak from the most recent qualifying days."""
        if not qualifying_dates:
            return 0

        # Parse dates
        date_objs = []
        for d in qualifying_dates:
            try:
                parsed = datetime.strptime(d, "%Y-%m-%d").date()
                date_objs.append(parsed)
            except ValueError:
                continue

        if not date_objs:
            return 0

        # Sort descending (most recent first)
        date_objs.sort(reverse=True)

        # Get today's date
        today = date.today()
        yesterday = today - timedelta(days=1)

        # Calculate consecutive qualifying days from the most recent
        streak = 0
        check_date = today

        # Check if today qualifies
        # If the most recent qualifying date is today or yesterday, start counting
        if date_objs[0] >= today:
            # Today qualifies
            streak = 1
            check_date = yesterday
        elif date_objs[0] >= yesterday:
            # Yesterday qualifies, check today
            streak = 0
            check_date = yesterday
        else:
            # Streak is broken
            return 0

        # Count consecutive days backward
        qualifying_set = set(date_objs)
        examined = set()

        while check_date in qualifying_set and check_date not in examined:
            examined.add(check_date)
            streak += 1
            check_date = check_date - timedelta(days=1)

        # If we went back past the first qualifying date, cap at total
        return min(streak, len(qualifying_set))

    async def _calculate_longest_streak(self, qualifying_dates: List[str]) -> int:
        """Calculate the longest consecutive qualifying streak."""
        if not qualifying_dates:
            return 0

        # Parse dates
        date_objs = []
        for d in qualifying_dates:
            try:
                parsed = datetime.strptime(d, "%Y-%m-%d").date()
                date_objs.append(parsed)
            except ValueError:
                continue

        if not date_objs:
            return 0

        # Sort ascending
        date_objs.sort()

        # Find longest consecutive run
        qualifying_set = set(date_objs)
        longest = 1
        current = 1

        for i in range(1, len(date_objs)):
            if date_objs[i] == date_objs[i - 1] + timedelta(days=1):
                current += 1
                longest = max(longest, current)
            else:
                current = 1

        return longest

    async def record_study_session(
        self,
        user_id: int,
        study_minutes: int,
        activity_count: int = 1,
        date_str: Optional[str] = None,
    ) -> DailyStudySummaryOut:
        """Record a study session and update streak."""
        # Use today's date if not provided
        if not date_str:
            today = datetime.utcnow().strftime("%Y-%m-%d")
            date_str = today

        # Check current maximum study minutes
        max_result = await self.db.execute(
            select(func.max(DailyStudySummary.study_minutes)).where(
                DailyStudySummary.user_id == user_id,
                DailyStudySummary.date != date_str
            )
        )
        previous_max = max_result.scalar() or 0

        # Check if a summary already exists for this date
        result = await self.db.execute(
            select(DailyStudySummary).where(
                DailyStudySummary.user_id == user_id,
                DailyStudySummary.date == date_str,
            )
        )
        summary = result.scalars().first()

        if summary:
            # Update existing summary
            summary.study_minutes += study_minutes
            summary.activity_count += activity_count
            # Re-qualify: a session qualifies if total for the day >= minimum
            summary.qualifying = summary.study_minutes >= MINIMUM_STUDY_MINUTES

            # Update total in user_streaks
            await self._update_streak_from_summary(user_id, summary)
        else:
            # Create new summary
            summary = DailyStudySummary(
                user_id=user_id,
                date=date_str,
                study_minutes=study_minutes,
                qualifying=study_minutes >= MINIMUM_STUDY_MINUTES,
                activity_count=activity_count,
            )
            self.db.add(summary)
            # Update total in user_streaks
            await self._update_streak_from_summary(user_id, summary)

        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(summary)

        is_new_record = False
        message = None
        if previous_max > 0 and summary.study_minutes > previous_max:
            is_new_record = True
            message = f"New record! You studied {summary.study_minutes} minutes today, beating your previous best of {previous_max} minutes!"

        return DailyStudySummaryOut(
            id=summary.id,
            user_id=summary.user_id,
            date=summary.date,
            study_minutes=summary.study_minutes,
            qualifying=summary.qualifying,
            activity_count=summary.activity_count,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
            is_new_record=is_new_record,
            message=message,
        )

    async def _update_streak_from_summary(
        self, user_id: int, summary: DailyStudySummary
    ) -> None:
        """Update user streak after a study summary change."""
        # Get all summaries for this user to recalculate streak
        result = await self.db.execute(
            select(DailyStudySummary)
            .where(DailyStudySummary.user_id == user_id)
            .order_by(DailyStudySummary.date.asc())
        )
        days = result.scalars().all()

        if not days:
            # No qualifying days
            streak_result = await self.db.execute(
                select(UserStreak).where(UserStreak.user_id == user_id)
            )
            streak = streak_result.scalars().first()
            if streak:
                streak.current_streak = 0
                streak.longest_streak = 0
                streak.total_study_days = 0
                streak.total_study_minutes = 0
                streak.last_qualifying_date = None
                await self.db.flush()
            return

        # Collect qualifying dates
        qualifying_dates = []
        total_minutes = 0

        for d in days:
            total_minutes += d.study_minutes if d.qualifying else 0
            if d.qualifying:
                qualifying_dates.append(d.date)

        # Calculate streaks
        current_streak = await self._calculate_current_streak(qualifying_dates)
        longest_streak = await self._calculate_longest_streak(qualifying_dates)
        total_study_days = len(qualifying_dates)
        last_qualifying_date = qualifying_dates[-1] if qualifying_dates else None

        # Update streak record
        streak_result = await self.db.execute(
            select(UserStreak).where(UserStreak.user_id == user_id)
        )
        streak = streak_result.scalars().first()
        if not streak:
            streak = UserStreak(user_id=user_id)
            self.db.add(streak)

        streak.current_streak = current_streak
        streak.longest_streak = longest_streak
        streak.total_study_days = total_study_days
        streak.total_study_minutes = total_minutes
        streak.last_qualifying_date = (
            datetime.fromisoformat(last_qualifying_date).replace(tzinfo=None)
            if last_qualifying_date
            else None
        )

        await self.db.flush()

    async def get_daily_summary(
        self, user_id: int, date_str: str
    ) -> Optional[DailyStudySummaryOut]:
        """Get daily study summary for a specific date."""
        result = await self.db.execute(
            select(DailyStudySummary).where(
                DailyStudySummary.user_id == user_id,
                DailyStudySummary.date == date_str,
            )
        )
        summary = result.scalars().first()
        if not summary:
            return None

        return DailyStudySummaryOut(
            id=summary.id,
            user_id=summary.user_id,
            date=summary.date,
            study_minutes=summary.study_minutes,
            qualifying=summary.qualifying,
            activity_count=summary.activity_count,
            created_at=summary.created_at,
            updated_at=summary.updated_at,
        )

    async def get_study_calendar(
        self,
        user_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get study calendar heatmap data (default: last 365 days)."""
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.utcnow().strftime("%Y-%m-%d")

        result = await self.db.execute(
            select(DailyStudySummary)
            .where(
                DailyStudySummary.user_id == user_id,
                DailyStudySummary.date >= start_date,
                DailyStudySummary.date <= end_date,
            )
            .order_by(DailyStudySummary.date.asc())
        )
        summaries = result.scalars().all()

        # Build calendar data
        calendar_data = []
        current = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        qualifying_set = set()

        while current <= end:
            # Find summary for this date
            summary = next(
                (s for s in summaries if s.date == current.strftime("%Y-%m-%d")), None
            )
            if summary:
                # Heatmap level: 0=none, 1=1-29min, 2=30-59min, 3=60-119min, 4=120+min
                minutes = summary.study_minutes
                if minutes >= 120:
                    level = 4
                elif minutes >= 60:
                    level = 3
                elif minutes >= 30:
                    level = 2
                elif minutes > 0:
                    level = 1
                else:
                    level = 0

                qualifying_set.add(current.strftime("%Y-%m-%d"))

                calendar_data.append(
                    {
                        "date": current.strftime("%Y-%m-%d"),
                        "dayOfWeek": current.strftime("%a"),
                        "studyMinutes": minutes,
                        "qualifying": summary.qualifying,
                        "heatmapLevel": level,
                    }
                )
            else:
                calendar_data.append(
                    {
                        "date": current.strftime("%Y-%m-%d"),
                        "dayOfWeek": current.strftime("%a"),
                        "studyMinutes": 0,
                        "qualifying": False,
                        "heatmapLevel": 0,
                    }
                )
            current = current + timedelta(days=1)

        return calendar_data