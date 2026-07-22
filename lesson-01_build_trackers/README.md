# Lesson 01 - Personal Trackers

Three personal tracking tools built with Python (stdlib only). Each runs a local HTTP server serving an interactive HTML page. Data is stored in JSON files alongside the scripts.

## Prerequisites

- Python 3.x

## Running the Trackers

From the project root, run any tracker with:

```bash
# Expense Tracker - http://localhost:8050
python3 lesson-01_build_trackers/personal-trackers/expense_tracker.py

# Exercise Tracker - http://localhost:8082
python3 lesson-01_build_trackers/personal-trackers/exercise_tracker.py

# Time Tracker - http://localhost:8090
python3 lesson-01_build_trackers/personal-trackers/time_tracker.py
```

Open the URL shown in the terminal in your browser. Press `Ctrl+C` to stop a tracker.

## Tracker Details

| Tracker  | Port | Data File           | Description                                      |
|----------|------|---------------------|--------------------------------------------------|
| Expense  | 8050 | `expenses.json`     | Track daily expenses by category (food, transport, utilities, entertainment, other) |
| Exercise | 8082 | `exercise_data.json`| Log workouts by type (cardio, strength, flexibility, sports, other) |
| Time     | 8090 | `time_data.json`    | Track time on tasks/projects with start/stop timers or manual entry |
