#!/usr/bin/env python3
"""Exercise Tracker - Log workouts and view exercise history."""

import json
import os
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "exercise_data.json")

EXERCISE_TYPES = ["cardio", "strength", "flexibility", "sports", "other"]


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Exercise Tracker</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #fdf6ec;
    color: #2d3436;
    min-height: 100vh;
  }
  header {
    background: #0d9488;
    color: #fdf6ec;
    padding: 1.5rem 2rem;
    text-align: center;
  }
  header h1 { font-size: 1.8rem; font-weight: 600; }
  header p { opacity: 0.85; margin-top: 0.3rem; font-size: 0.95rem; }
  .container { max-width: 900px; margin: 0 auto; padding: 1.5rem; }

  /* Tabs */
  .tabs {
    display: flex; gap: 0.5rem; margin-bottom: 1.5rem;
    border-bottom: 2px solid #0d9488;
    padding-bottom: 0;
  }
  .tab-btn {
    padding: 0.6rem 1.2rem;
    border: none; background: transparent;
    font-size: 0.95rem; cursor: pointer;
    color: #5f6368; font-weight: 500;
    border-bottom: 3px solid transparent;
    margin-bottom: -2px; transition: all 0.2s;
  }
  .tab-btn:hover { color: #0d9488; }
  .tab-btn.active {
    color: #0d9488;
    border-bottom-color: #0d9488;
  }
  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* Form */
  .form-card {
    background: #fff;
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  }
  .form-row {
    display: flex; gap: 1rem; flex-wrap: wrap;
    margin-bottom: 1rem;
  }
  .form-group { flex: 1; min-width: 180px; }
  .form-group label {
    display: block; font-size: 0.85rem;
    font-weight: 500; margin-bottom: 0.3rem; color: #444;
  }
  .form-group input, .form-group select {
    width: 100%; padding: 0.55rem 0.75rem;
    border: 1.5px solid #d1d5db; border-radius: 6px;
    font-size: 0.95rem; outline: none;
    transition: border-color 0.2s;
  }
  .form-group input:focus, .form-group select:focus {
    border-color: #0d9488;
  }
  .optional-fields { margin-top: 0.5rem; }
  .optional-fields h4 {
    font-size: 0.85rem; color: #888; margin-bottom: 0.5rem;
  }
  #strength-fields, #cardio-fields { display: none; }
  .btn {
    padding: 0.6rem 1.5rem; border: none; border-radius: 6px;
    font-size: 0.95rem; font-weight: 500; cursor: pointer;
    transition: background 0.2s;
  }
  .btn-primary { background: #0d9488; color: #fff; margin-top: 0.5rem; }
  .btn-primary:hover { background: #0f766e; }
  .btn-danger {
    background: transparent; color: #dc2626;
    font-size: 0.8rem; padding: 0.3rem 0.7rem;
    border: 1px solid #dc2626; border-radius: 4px;
  }
  .btn-danger:hover { background: #dc2626; color: #fff; }

  /* Table */
  .table-card {
    background: #fff; border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    overflow: hidden;
  }
  table { width: 100%; border-collapse: collapse; }
  th {
    background: #0d9488; color: #fdf6ec;
    text-align: left; padding: 0.7rem 1rem;
    font-size: 0.85rem; font-weight: 600;
  }
  td {
    padding: 0.65rem 1rem; border-bottom: 1px solid #f0ebe3;
    font-size: 0.9rem;
  }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #f9f5ee; }
  .type-badge {
    display: inline-block; padding: 0.15rem 0.6rem;
    border-radius: 999px; font-size: 0.78rem; font-weight: 500;
  }
  .type-cardio { background: #ccfbf1; color: #0f766e; }
  .type-strength { background: #dbeafe; color: #1e40af; }
  .type-flexibility { background: #fce7f3; color: #9d174d; }
  .type-sports { background: #fef3c7; color: #92400e; }
  .type-other { background: #e5e7eb; color: #374151; }

  /* Summary */
  .summary-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 1rem;
  }
  .summary-card {
    background: #fff; border-radius: 10px;
    padding: 1.2rem; text-align: center;
    box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    border-top: 4px solid #0d9488;
  }
  .summary-card h3 {
    text-transform: capitalize;
    font-size: 1rem; color: #0d9488; margin-bottom: 0.5rem;
  }
  .summary-card .count { font-size: 2rem; font-weight: 700; color: #2d3436; }
  .summary-card .detail { font-size: 0.82rem; color: #888; margin-top: 0.3rem; }

  .empty-state {
    text-align: center; padding: 3rem 1rem; color: #aaa;
  }
  .empty-state p { font-size: 1.1rem; }

  .msg {
    padding: 0.7rem 1rem; border-radius: 6px;
    margin-bottom: 1rem; font-size: 0.9rem; display: none;
  }
  .msg-success { background: #ccfbf1; color: #0f766e; }
  .msg-error { background: #fee2e2; color: #991b1b; }
</style>
</head>
<body>

<header>
  <h1>Exercise Tracker</h1>
  <p>Log workouts and track your progress</p>
</header>

<div class="container">
  <div id="msg" class="msg"></div>

  <div class="tabs">
    <button class="tab-btn active" data-tab="add">Add Exercise</button>
    <button class="tab-btn" data-tab="history">History</button>
    <button class="tab-btn" data-tab="summary">Summary</button>
  </div>

  <!-- Add Exercise -->
  <div id="tab-add" class="tab-content active">
    <div class="form-card">
      <form id="exercise-form" action="javascript:void(0)">
        <div class="form-row">
          <div class="form-group">
            <label for="ex-type">Type</label>
            <select id="ex-type" name="type" required>
              <option value="">Select type</option>
              <option value="cardio">Cardio</option>
              <option value="strength">Strength</option>
              <option value="flexibility">Flexibility</option>
              <option value="sports">Sports</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div class="form-group">
            <label for="ex-name">Exercise Name</label>
            <input type="text" id="ex-name" name="name" placeholder="e.g. Running" required>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label for="ex-duration">Duration (minutes)</label>
            <input type="number" id="ex-duration" name="duration" min="1" placeholder="30" required>
          </div>
          <div class="form-group">
            <label for="ex-date">Date</label>
            <input type="date" id="ex-date" name="date" required>
          </div>
        </div>

        <!-- Cardio optional fields -->
        <div id="cardio-fields" class="optional-fields">
          <h4>Cardio Details (optional)</h4>
          <div class="form-row">
            <div class="form-group">
              <label for="ex-distance">Distance (km)</label>
              <input type="number" id="ex-distance" name="distance" step="0.1" min="0" placeholder="5.0">
            </div>
          </div>
        </div>

        <!-- Strength optional fields -->
        <div id="strength-fields" class="optional-fields">
          <h4>Strength Details (optional)</h4>
          <div class="form-row">
            <div class="form-group">
              <label for="ex-sets">Sets</label>
              <input type="number" id="ex-sets" name="sets" min="1" placeholder="3">
            </div>
            <div class="form-group">
              <label for="ex-reps">Reps</label>
              <input type="number" id="ex-reps" name="reps" min="1" placeholder="12">
            </div>
            <div class="form-group">
              <label for="ex-weight">Weight (kg)</label>
              <input type="number" id="ex-weight" name="weight" step="0.5" min="0" placeholder="20">
            </div>
          </div>
        </div>

        <button type="submit" class="btn btn-primary">Add Exercise</button>
      </form>
    </div>
  </div>

  <!-- History -->
  <div id="tab-history" class="tab-content">
    <div id="history-content"></div>
  </div>

  <!-- Summary -->
  <div id="tab-summary" class="tab-content">
    <div id="summary-content"></div>
  </div>
</div>

<script>
  const API = '';

  // Tabs
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
      if (btn.dataset.tab === 'history') loadHistory();
      if (btn.dataset.tab === 'summary') loadSummary();
    });
  });

  // Toggle optional fields based on type
  document.getElementById('ex-type').addEventListener('change', function() {
    document.getElementById('cardio-fields').style.display = this.value === 'cardio' ? 'block' : 'none';
    document.getElementById('strength-fields').style.display = this.value === 'strength' ? 'block' : 'none';
  });

  // Set default date to today
  document.getElementById('ex-date').value = new Date().toISOString().split('T')[0];

  function showMsg(text, type) {
    const el = document.getElementById('msg');
    el.textContent = text;
    el.className = 'msg msg-' + type;
    el.style.display = 'block';
    setTimeout(() => { el.style.display = 'none'; }, 3000);
  }

  // Add exercise
  document.getElementById('exercise-form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const data = {
      type: document.getElementById('ex-type').value,
      name: document.getElementById('ex-name').value,
      duration: parseInt(document.getElementById('ex-duration').value),
      date: document.getElementById('ex-date').value,
    };
    if (data.type === 'cardio') {
      const d = document.getElementById('ex-distance').value;
      if (d) data.distance = parseFloat(d);
    }
    if (data.type === 'strength') {
      const s = document.getElementById('ex-sets').value;
      const r = document.getElementById('ex-reps').value;
      const w = document.getElementById('ex-weight').value;
      if (s) data.sets = parseInt(s);
      if (r) data.reps = parseInt(r);
      if (w) data.weight = parseFloat(w);
    }
    try {
      const res = await fetch(API + '/api/exercises', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(data),
      });
      if (res.ok) {
        showMsg('Exercise added!', 'success');
        this.reset();
        document.getElementById('ex-date').value = new Date().toISOString().split('T')[0];
        document.getElementById('cardio-fields').style.display = 'none';
        document.getElementById('strength-fields').style.display = 'none';
      } else {
        const err = await res.json();
        showMsg(err.error || 'Failed to add exercise', 'error');
      }
    } catch (err) {
      showMsg('Connection error', 'error');
    }
  });

  // Load history
  async function loadHistory() {
    const container = document.getElementById('history-content');
    try {
      const res = await fetch(API + '/api/exercises');
      const exercises = await res.json();
      if (exercises.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No exercises logged yet.</p></div>';
        return;
      }
      let details = '';
      let html = '<div class="table-card"><table><thead><tr>'
        + '<th>Date</th><th>Type</th><th>Name</th><th>Duration</th><th>Details</th><th></th>'
        + '</tr></thead><tbody>';
      exercises.forEach(ex => {
        details = '';
        if (ex.type === 'cardio' && ex.distance) details = ex.distance + ' km';
        if (ex.type === 'strength') {
          const parts = [];
          if (ex.sets) parts.push(ex.sets + ' sets');
          if (ex.reps) parts.push(ex.reps + ' reps');
          if (ex.weight) parts.push(ex.weight + ' kg');
          details = parts.join(', ');
        }
        html += '<tr>'
          + '<td>' + ex.date + '</td>'
          + '<td><span class="type-badge type-' + ex.type + '">' + ex.type + '</span></td>'
          + '<td>' + escapeHtml(ex.name) + '</td>'
          + '<td>' + ex.duration + ' min</td>'
          + '<td>' + details + '</td>'
          + '<td><button class="btn btn-danger" onclick="deleteExercise(\\'' + ex.id + '\\')">Delete</button></td>'
          + '</tr>';
      });
      html += '</tbody></table></div>';
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = '<div class="empty-state"><p>Failed to load exercises.</p></div>';
    }
  }

  // Delete exercise
  async function deleteExercise(id) {
    if (!confirm('Delete this exercise?')) return;
    try {
      const res = await fetch(API + '/api/exercises/' + id, { method: 'DELETE' });
      if (res.ok) {
        showMsg('Exercise deleted', 'success');
        loadHistory();
      } else {
        showMsg('Failed to delete', 'error');
      }
    } catch (err) {
      showMsg('Connection error', 'error');
    }
  }

  // Load summary
  async function loadSummary() {
    const container = document.getElementById('summary-content');
    try {
      const res = await fetch(API + '/api/summary');
      const summary = await res.json();
      if (Object.keys(summary).length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No exercises to summarize.</p></div>';
        return;
      }
      let html = '<div class="summary-grid">';
      for (const [type, info] of Object.entries(summary)) {
        let detail = 'Total: ' + info.total_duration + ' min';
        if (type === 'cardio' && info.total_distance) {
          detail += ' | ' + info.total_distance + ' km';
        }
        html += '<div class="summary-card">'
          + '<h3>' + type + '</h3>'
          + '<div class="count">' + info.count + '</div>'
          + '<div class="detail">workouts</div>'
          + '<div class="detail">' + detail + '</div>'
          + '</div>';
      }
      html += '</div>';
      container.innerHTML = html;
    } catch (err) {
      container.innerHTML = '<div class="empty-state"><p>Failed to load summary.</p></div>';
    }
  }

  function escapeHtml(text) {
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
  }
</script>

</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == "/api/exercises":
            exercises = load_data()
            exercises.sort(key=lambda x: x.get("date", ""), reverse=True)
            self.send_json(200, exercises)
        elif self.path == "/api/summary":
            exercises = load_data()
            summary = {}
            for ex in exercises:
                t = ex["type"]
                if t not in summary:
                    summary[t] = {"count": 0, "total_duration": 0}
                    if t == "cardio":
                        summary[t]["total_distance"] = 0
                summary[t]["count"] += 1
                summary[t]["total_duration"] += ex.get("duration", 0)
                if t == "cardio" and ex.get("distance"):
                    summary[t]["total_distance"] = round(
                        summary[t]["total_distance"] + ex["distance"], 1
                    )
            self.send_json(200, summary)
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path.rstrip("/") == "/api/exercises":
            body = self.read_body()
            if not body:
                self.send_json(400, {"error": "Invalid JSON"})
                return
            required = ["type", "name", "duration", "date"]
            for field in required:
                if field not in body or not body[field]:
                    self.send_json(400, {"error": f"Missing field: {field}"})
                    return
            if body["type"] not in EXERCISE_TYPES:
                self.send_json(400, {"error": f"Invalid type. Must be one of: {', '.join(EXERCISE_TYPES)}"})
                return
            exercise = {
                "id": uuid.uuid4().hex[:8],
                "type": body["type"],
                "name": body["name"],
                "duration": int(body["duration"]),
                "date": body["date"],
            }
            if body["type"] == "cardio" and body.get("distance"):
                exercise["distance"] = float(body["distance"])
            if body["type"] == "strength":
                if body.get("sets"):
                    exercise["sets"] = int(body["sets"])
                if body.get("reps"):
                    exercise["reps"] = int(body["reps"])
                if body.get("weight"):
                    exercise["weight"] = float(body["weight"])
            data = load_data()
            data.append(exercise)
            save_data(data)
            self.send_json(201, exercise)
        else:
            self.send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        if self.path.startswith("/api/exercises/"):
            exercise_id = self.path.split("/")[-1]
            data = load_data()
            new_data = [e for e in data if e["id"] != exercise_id]
            if len(new_data) == len(data):
                self.send_json(404, {"error": "Exercise not found"})
                return
            save_data(new_data)
            self.send_json(200, {"status": "deleted"})
        else:
            self.send_json(404, {"error": "Not found"})

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        try:
            return json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            return None

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


def main():
    port = 8082
    server = HTTPServer(("localhost", port), Handler)
    print(f"Exercise Tracker running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
