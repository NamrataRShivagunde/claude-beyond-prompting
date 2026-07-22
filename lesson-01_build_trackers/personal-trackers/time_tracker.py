#!/usr/bin/env python3
"""Time Tracker - Track time spent on tasks and projects.

Serves an HTML interface for starting/stopping timers, logging time manually,
viewing entries, and viewing summaries grouped by project.
"""

import json
import os
import http.server
import urllib.parse
import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "time_data.json")


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"entries": [], "active_timer": None}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Time Tracker</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: #FFF5EE;
    color: #5D4037;
    min-height: 100vh;
  }
  header {
    background: #FFAB91;
    padding: 24px;
    text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  header h1 { font-size: 28px; color: #4E342E; }
  header p { color: #6D4C41; margin-top: 4px; }

  .container { max-width: 900px; margin: 24px auto; padding: 0 16px; }

  .tabs {
    display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap;
  }
  .tab-btn {
    padding: 10px 20px; border: 2px solid #FFAB91; border-radius: 8px;
    background: #FFFAF7; color: #5D4037; cursor: pointer; font-size: 15px;
    font-weight: 500; transition: all 0.2s;
  }
  .tab-btn:hover { background: #FFE0D0; }
  .tab-btn.active { background: #FFAB91; color: #4E342E; font-weight: 600; }

  .panel { display: none; }
  .panel.active { display: block; }

  .card {
    background: #FFFAF7; border: 1px solid #FFCCBC; border-radius: 12px;
    padding: 24px; margin-bottom: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  }
  .card h2 { color: #E64A19; margin-bottom: 16px; font-size: 20px; }

  label { display: block; font-weight: 500; margin-bottom: 4px; margin-top: 12px; }
  input, select {
    width: 100%; padding: 10px 12px; border: 1px solid #FFCCBC; border-radius: 8px;
    font-size: 15px; background: #FFF; color: #5D4037; outline: none;
  }
  input:focus, select:focus { border-color: #FFAB91; box-shadow: 0 0 0 3px rgba(255,171,145,0.3); }

  .btn {
    padding: 10px 24px; border: none; border-radius: 8px; font-size: 15px;
    font-weight: 600; cursor: pointer; transition: all 0.2s; margin-top: 16px;
  }
  .btn-primary { background: #FF8A65; color: #fff; }
  .btn-primary:hover { background: #FF7043; }
  .btn-stop { background: #E64A19; color: #fff; }
  .btn-stop:hover { background: #D84315; }
  .btn-delete { background: transparent; color: #E64A19; border: 1px solid #E64A19; padding: 6px 14px; font-size: 13px; margin-top: 0; }
  .btn-delete:hover { background: #FFEBE5; }

  .timer-display {
    text-align: center; padding: 20px; background: #FFE0D0; border-radius: 12px;
    margin-bottom: 16px;
  }
  .timer-display .time { font-size: 42px; font-weight: 700; color: #E64A19; font-variant-numeric: tabular-nums; }
  .timer-display .task-name { font-size: 16px; color: #6D4C41; margin-top: 4px; }

  .no-timer { text-align: center; color: #A1887F; padding: 20px; }

  table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  th { text-align: left; padding: 10px 12px; background: #FFCCBC; color: #4E342E; font-size: 14px; }
  th:first-child { border-radius: 8px 0 0 0; }
  th:last-child { border-radius: 0 8px 0 0; }
  td { padding: 10px 12px; border-bottom: 1px solid #FFE0D0; font-size: 14px; }
  tr:hover td { background: #FFF0E8; }

  .summary-project { margin-bottom: 16px; }
  .summary-project h3 {
    background: #FFCCBC; padding: 10px 16px; border-radius: 8px 8px 0 0;
    color: #4E342E; font-size: 16px; display: flex; justify-content: space-between;
  }
  .summary-entries {
    border: 1px solid #FFCCBC; border-top: none; border-radius: 0 0 8px 8px;
    padding: 8px 16px;
  }
  .summary-entry { padding: 6px 0; border-bottom: 1px solid #FFE0D0; font-size: 14px;
    display: flex; justify-content: space-between; }
  .summary-entry:last-child { border-bottom: none; }

  .empty-msg { text-align: center; color: #A1887F; padding: 40px 20px; font-size: 16px; }

  .msg {
    padding: 12px 16px; border-radius: 8px; margin-bottom: 16px; font-size: 14px;
  }
  .msg-success { background: #E8F5E9; color: #2E7D32; border: 1px solid #A5D6A7; }
  .msg-error { background: #FFEBE5; color: #C62828; border: 1px solid #EF9A9A; }
</style>
</head>
<body>
<header>
  <h1>Time Tracker</h1>
  <p>Track time spent on tasks and projects</p>
</header>
<div class="container">
  <div class="tabs">
    <button class="tab-btn active" onclick="showTab('timer')">Timer</button>
    <button class="tab-btn" onclick="showTab('manual')">Log Manually</button>
    <button class="tab-btn" onclick="showTab('entries')">All Entries</button>
    <button class="tab-btn" onclick="showTab('summary')">Summary</button>
  </div>

  <div id="msg"></div>

  <!-- Timer Panel -->
  <div id="timer" class="panel active">
    <div class="card">
      <h2>Timer</h2>
      <div id="timer-area"></div>
    </div>
  </div>

  <!-- Manual Entry Panel -->
  <div id="manual" class="panel">
    <div class="card">
      <h2>Log Time Manually</h2>
      <form id="manual-form" onsubmit="return submitManual(event)">
        <label for="m-task">Task</label>
        <input type="text" id="m-task" required placeholder="e.g. Write report">
        <label for="m-project">Project</label>
        <input type="text" id="m-project" placeholder="e.g. Work (optional)">
        <label for="m-duration">Duration (minutes)</label>
        <input type="number" id="m-duration" required min="1" placeholder="e.g. 45">
        <label for="m-date">Date</label>
        <input type="date" id="m-date" required>
        <button type="submit" class="btn btn-primary">Log Entry</button>
      </form>
    </div>
  </div>

  <!-- All Entries Panel -->
  <div id="entries" class="panel">
    <div class="card">
      <h2>All Time Entries</h2>
      <div id="entries-table"></div>
    </div>
  </div>

  <!-- Summary Panel -->
  <div id="summary" class="panel">
    <div class="card">
      <h2>Summary by Project</h2>
      <div id="summary-area"></div>
    </div>
  </div>
</div>

<script>
  let timerInterval = null;

  function showTab(name) {
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(name).classList.add('active');
    document.querySelector('[onclick="showTab(\\''+name+'\\')"]').classList.add('active');
    if (name === 'entries') loadEntries();
    if (name === 'summary') loadSummary();
    if (name === 'timer') loadTimer();
  }

  function showMsg(text, type) {
    const el = document.getElementById('msg');
    el.innerHTML = '<div class="msg msg-' + type + '">' + text + '</div>';
    setTimeout(() => el.innerHTML = '', 4000);
  }

  function api(action, body) {
    return fetch('/api', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action, ...body})
    }).then(r => r.json());
  }

  // -- Timer --
  function loadTimer() {
    api('get_timer').then(d => renderTimer(d));
  }

  function renderTimer(data) {
    const area = document.getElementById('timer-area');
    if (data.active) {
      const started = new Date(data.active.started).getTime();
      area.innerHTML = `
        <div class="timer-display">
          <div class="time" id="elapsed">00:00:00</div>
          <div class="task-name">${esc(data.active.task)}${data.active.project ? ' - ' + esc(data.active.project) : ''}</div>
        </div>
        <div style="text-align:center">
          <button class="btn btn-stop" onclick="stopTimer()">Stop Timer</button>
        </div>`;
      if (timerInterval) clearInterval(timerInterval);
      function tick() {
        const diff = Math.floor((Date.now() - started) / 1000);
        const h = String(Math.floor(diff / 3600)).padStart(2, '0');
        const m = String(Math.floor((diff % 3600) / 60)).padStart(2, '0');
        const s = String(diff % 60).padStart(2, '0');
        const el = document.getElementById('elapsed');
        if (el) el.textContent = h + ':' + m + ':' + s;
      }
      tick();
      timerInterval = setInterval(tick, 1000);
    } else {
      if (timerInterval) { clearInterval(timerInterval); timerInterval = null; }
      area.innerHTML = `
        <div class="no-timer">No active timer</div>
        <form onsubmit="return startTimer(event)">
          <label for="t-task">Task</label>
          <input type="text" id="t-task" required placeholder="e.g. Design mockups">
          <label for="t-project">Project</label>
          <input type="text" id="t-project" placeholder="e.g. Client A (optional)">
          <button type="submit" class="btn btn-primary">Start Timer</button>
        </form>`;
    }
  }

  function startTimer(e) {
    e.preventDefault();
    const task = document.getElementById('t-task').value.trim();
    const project = document.getElementById('t-project').value.trim();
    if (!task) return;
    api('start_timer', {task, project}).then(d => {
      if (d.error) showMsg(d.error, 'error');
      else { showMsg('Timer started!', 'success'); renderTimer(d); }
    });
    return false;
  }

  function stopTimer() {
    api('stop_timer').then(d => {
      if (d.error) showMsg(d.error, 'error');
      else { showMsg('Timer stopped. ' + d.duration + ' min logged.', 'success'); renderTimer(d); }
    });
  }

  // -- Manual --
  function submitManual(e) {
    e.preventDefault();
    const task = document.getElementById('m-task').value.trim();
    const project = document.getElementById('m-project').value.trim();
    const duration = parseInt(document.getElementById('m-duration').value);
    const date = document.getElementById('m-date').value;
    if (!task || !duration || !date) return false;
    api('add_manual', {task, project, duration, date}).then(d => {
      if (d.error) showMsg(d.error, 'error');
      else {
        showMsg('Entry logged!', 'success');
        document.getElementById('manual-form').reset();
        document.getElementById('m-date').value = new Date().toISOString().slice(0,10);
      }
    });
    return false;
  }

  // -- Entries --
  function loadEntries() {
    api('get_entries').then(d => {
      const area = document.getElementById('entries-table');
      if (!d.entries || d.entries.length === 0) {
        area.innerHTML = '<div class="empty-msg">No entries yet. Start a timer or log time manually.</div>';
        return;
      }
      let html = '<table><tr><th>Date</th><th>Task</th><th>Project</th><th>Duration</th><th></th></tr>';
      d.entries.forEach((e, i) => {
        html += `<tr>
          <td>${esc(e.date)}</td>
          <td>${esc(e.task)}</td>
          <td>${esc(e.project || '-')}</td>
          <td>${e.duration} min</td>
          <td><button class="btn btn-delete" onclick="deleteEntry(${i})">Delete</button></td>
        </tr>`;
      });
      html += '</table>';
      area.innerHTML = html;
    });
  }

  function deleteEntry(idx) {
    api('delete_entry', {index: idx}).then(d => {
      if (d.error) showMsg(d.error, 'error');
      else { showMsg('Entry deleted.', 'success'); loadEntries(); }
    });
  }

  // -- Summary --
  function loadSummary() {
    api('get_summary').then(d => {
      const area = document.getElementById('summary-area');
      if (!d.projects || Object.keys(d.projects).length === 0) {
        area.innerHTML = '<div class="empty-msg">No entries to summarize.</div>';
        return;
      }
      let html = '';
      for (const [proj, info] of Object.entries(d.projects)) {
        html += `<div class="summary-project">
          <h3><span>${esc(proj)}</span><span>${info.total} min</span></h3>
          <div class="summary-entries">`;
        info.tasks.forEach(t => {
          html += `<div class="summary-entry"><span>${esc(t.task)}</span><span>${t.duration} min</span></div>`;
        });
        html += '</div></div>';
      }
      area.innerHTML = html;
    });
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // Init
  document.getElementById('m-date').value = new Date().toISOString().slice(0,10);
  loadTimer();
</script>
</body>
</html>"""


class TimeTrackerHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.encode())

    def do_POST(self):
        if self.path != "/api":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}
        action = body.get("action", "")

        data = load_data()
        result = {}

        if action == "get_timer":
            result = {"active": data.get("active_timer")}

        elif action == "start_timer":
            if data.get("active_timer"):
                result = {"error": "A timer is already running. Stop it first."}
            else:
                data["active_timer"] = {
                    "task": body["task"],
                    "project": body.get("project", ""),
                    "started": datetime.datetime.now().isoformat(),
                }
                save_data(data)
                result = {"active": data["active_timer"]}

        elif action == "stop_timer":
            timer = data.get("active_timer")
            if not timer:
                result = {"error": "No active timer to stop."}
            else:
                started = datetime.datetime.fromisoformat(timer["started"])
                elapsed = (datetime.datetime.now() - started).total_seconds()
                duration = max(1, round(elapsed / 60))
                entry = {
                    "task": timer["task"],
                    "project": timer.get("project", ""),
                    "duration": duration,
                    "date": started.strftime("%Y-%m-%d"),
                }
                data["entries"].append(entry)
                data["active_timer"] = None
                save_data(data)
                result = {"active": None, "duration": duration}

        elif action == "add_manual":
            entry = {
                "task": body["task"],
                "project": body.get("project", ""),
                "duration": int(body["duration"]),
                "date": body["date"],
            }
            data["entries"].append(entry)
            save_data(data)
            result = {"ok": True}

        elif action == "get_entries":
            sorted_entries = sorted(data["entries"], key=lambda e: e["date"], reverse=True)
            result = {"entries": sorted_entries}

        elif action == "delete_entry":
            idx = body.get("index")
            sorted_entries = sorted(data["entries"], key=lambda e: e["date"], reverse=True)
            if idx is not None and 0 <= idx < len(sorted_entries):
                entry_to_remove = sorted_entries[idx]
                data["entries"].remove(entry_to_remove)
                save_data(data)
                result = {"ok": True}
            else:
                result = {"error": "Invalid entry index."}

        elif action == "get_summary":
            projects = {}
            for e in data["entries"]:
                proj = e.get("project") or "(No project)"
                if proj not in projects:
                    projects[proj] = {"total": 0, "tasks": []}
                projects[proj]["total"] += e["duration"]
                projects[proj]["tasks"].append({"task": e["task"], "duration": e["duration"]})
            result = {"projects": projects}

        else:
            result = {"error": "Unknown action."}

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())

    def log_message(self, format, *args):
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    port = 8090
    server = http.server.HTTPServer(("localhost", port), TimeTrackerHandler)
    print(f"Time Tracker running at http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
