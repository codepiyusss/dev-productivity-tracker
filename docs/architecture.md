# Architecture

The application uses Python modules for tasks, storage and analytics.

## Streaks

`src/streaks.py` (`StreakTracker`) derives streaks from `tasks.completed_at`.
A streak is consecutive days with at least one completed task. It stays alive
through the end of the following day, so completing nothing yet today does not
reset it. Tasks completed before completion times were tracked have no
timestamp and are ignored. The goal streak counts days where the number of
completed tasks reached the daily goal.

## Time tracking

`src/timetracking.py` (`TimeTracker`) implements start, stop, status, manual
logging, listing and summaries. All methods that depend on the current time
accept a `now` argument so they can be tested with fixed dates.
`src/utils.py` provides `parse_duration` (`45`, `45m`, `1h30m`, `1:30`) and
`format_duration`.
