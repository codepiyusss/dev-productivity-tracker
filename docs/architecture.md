# Architecture

The application uses Python modules for tasks, storage and analytics.

## Streaks

`src/streaks.py` (`StreakTracker`) derives streaks from `tasks.completed_at`.
A streak is consecutive days with at least one completed task. It stays alive
through the end of the following day, so completing nothing yet today does not
reset it. Tasks completed before completion times were tracked have no
timestamp and are ignored. The goal streak counts days where the number of
completed tasks reached the daily goal.
