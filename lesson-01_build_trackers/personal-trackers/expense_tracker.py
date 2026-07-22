#!/usr/bin/env python3
"""Expense Tracker - Track personal daily expenses with categories and summaries."""

import json
import os
import uuid
import webbrowser
import http.server
import urllib.parse
from datetime import datetime

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.json")
CATEGORIES = ["food", "transport", "utilities", "entertainment", "other"]
PORT = 8050


def load_expenses():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []


def save_expenses(expenses):
    with open(DATA_FILE, "w") as f:
        json.dump(expenses, f, indent=2)


def build_html(expenses, message=""):
    category_totals = {}
    for cat in CATEGORIES:
        category_totals[cat] = 0.0
    for exp in expenses:
        category_totals[exp["category"]] += exp["amount"]
    grand_total = sum(category_totals.values())

    expense_rows = ""
    for exp in reversed(expenses):
        expense_rows += f"""
        <tr>
          <td>{exp["date"]}</td>
          <td><span class="cat-badge cat-{exp['category']}">{exp["category"]}</span></td>
          <td>${exp["amount"]:.2f}</td>
          <td>{exp["description"]}</td>
          <td>
            <form method="POST" action="/delete" style="margin:0">
              <input type="hidden" name="id" value="{exp['id']}">
              <button type="submit" class="btn-delete" title="Delete">&#x2715;</button>
            </form>
          </td>
        </tr>"""

    if not expenses:
        expense_rows = '<tr><td colspan="5" class="empty-msg">No expenses yet. Add one above!</td></tr>'

    summary_rows = ""
    for cat in CATEGORIES:
        total = category_totals[cat]
        pct = (total / grand_total * 100) if grand_total > 0 else 0
        summary_rows += f"""
        <tr>
          <td><span class="cat-badge cat-{cat}">{cat}</span></td>
          <td>${total:.2f}</td>
          <td>
            <div class="bar-container">
              <div class="bar cat-bg-{cat}" style="width:{pct:.1f}%"></div>
            </div>
          </td>
          <td>{pct:.1f}%</td>
        </tr>"""

    message_html = ""
    if message:
        message_html = f'<div class="message">{message}</div>'

    category_options = "".join(
        f'<option value="{c}">{c.capitalize()}</option>' for c in CATEGORIES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Expense Tracker</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #FFF8F0;
    color: #1a1a2e;
    min-height: 100vh;
  }}
  header {{
    background: linear-gradient(135deg, #1e3a5f, #2e6b9e);
    color: #FFF8F0;
    padding: 24px 0;
    text-align: center;
    box-shadow: 0 2px 12px rgba(30,58,95,0.2);
  }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; letter-spacing: 0.5px; }}
  header p {{ font-size: 0.95rem; opacity: 0.85; margin-top: 4px; }}
  .container {{ max-width: 900px; margin: 0 auto; padding: 24px 16px; }}
  .card {{
    background: #fff;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(30,58,95,0.08);
    padding: 24px;
    margin-bottom: 24px;
    border: 1px solid #e8ddd0;
  }}
  .card h2 {{
    font-size: 1.15rem;
    color: #1e3a5f;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e8ddd0;
  }}
  .message {{
    background: #d4edda;
    color: #155724;
    padding: 10px 16px;
    border-radius: 8px;
    margin-bottom: 16px;
    font-size: 0.9rem;
  }}
  .add-form {{ display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }}
  .form-group {{ display: flex; flex-direction: column; gap: 4px; }}
  .form-group label {{ font-size: 0.8rem; color: #555; font-weight: 600; }}
  .form-group input, .form-group select {{
    padding: 8px 12px;
    border: 1px solid #ccc;
    border-radius: 6px;
    font-size: 0.9rem;
    background: #FFFDF7;
  }}
  .form-group input:focus, .form-group select:focus {{
    outline: none;
    border-color: #2e6b9e;
    box-shadow: 0 0 0 2px rgba(46,107,158,0.15);
  }}
  .btn-add {{
    background: linear-gradient(135deg, #1e3a5f, #2e6b9e);
    color: white;
    border: none;
    padding: 8px 20px;
    border-radius: 6px;
    font-size: 0.9rem;
    cursor: pointer;
    font-weight: 600;
    height: 36px;
  }}
  .btn-add:hover {{ opacity: 0.9; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    text-align: left;
    padding: 10px 12px;
    background: #f0e6d6;
    color: #1e3a5f;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  td {{ padding: 10px 12px; border-bottom: 1px solid #f0e6d6; font-size: 0.9rem; }}
  tr:hover {{ background: #FFFDF7; }}
  .empty-msg {{ text-align: center; color: #999; padding: 24px; font-style: italic; }}
  .cat-badge {{
    display: inline-block;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.78rem;
    font-weight: 600;
    text-transform: capitalize;
  }}
  .cat-food {{ background: #e8f5e9; color: #2e7d32; }}
  .cat-transport {{ background: #e3f2fd; color: #1565c0; }}
  .cat-utilities {{ background: #fff3e0; color: #e65100; }}
  .cat-entertainment {{ background: #f3e5f5; color: #7b1fa2; }}
  .cat-other {{ background: #eceff1; color: #37474f; }}
  .cat-bg-food {{ background: #66bb6a; }}
  .cat-bg-transport {{ background: #42a5f5; }}
  .cat-bg-utilities {{ background: #ffa726; }}
  .cat-bg-entertainment {{ background: #ab47bc; }}
  .cat-bg-other {{ background: #78909c; }}
  .btn-delete {{
    background: none;
    border: 1px solid #e0e0e0;
    color: #c0392b;
    cursor: pointer;
    font-size: 0.85rem;
    border-radius: 4px;
    padding: 2px 8px;
  }}
  .btn-delete:hover {{ background: #fdecea; border-color: #c0392b; }}
  .bar-container {{
    background: #f0e6d6;
    border-radius: 6px;
    height: 14px;
    width: 100%;
    overflow: hidden;
  }}
  .bar {{ height: 100%; border-radius: 6px; transition: width 0.3s; }}
  .grand-total {{
    text-align: right;
    font-size: 1.1rem;
    font-weight: 700;
    color: #1e3a5f;
    padding: 12px;
    border-top: 2px solid #e8ddd0;
    margin-top: 8px;
  }}
  @media (max-width: 600px) {{
    .add-form {{ flex-direction: column; }}
    .form-group {{ width: 100%; }}
    .btn-add {{ width: 100%; }}
  }}
</style>
</head>
<body>
<header>
  <h1>Expense Tracker</h1>
  <p>Track your daily spending</p>
</header>
<div class="container">
  {message_html}
  <div class="card">
    <h2>Add Expense</h2>
    <form method="POST" action="/add" class="add-form">
      <div class="form-group">
        <label>Date</label>
        <input type="date" name="date" value="{datetime.now().strftime('%Y-%m-%d')}" required>
      </div>
      <div class="form-group">
        <label>Category</label>
        <select name="category" required>
          {category_options}
        </select>
      </div>
      <div class="form-group">
        <label>Amount ($)</label>
        <input type="number" name="amount" step="0.01" min="0.01" placeholder="0.00" required>
      </div>
      <div class="form-group" style="flex:1">
        <label>Description</label>
        <input type="text" name="description" placeholder="What was it for?" required>
      </div>
      <button type="submit" class="btn-add">Add</button>
    </form>
  </div>

  <div class="card">
    <h2>Summary by Category</h2>
    <table>
      <thead><tr><th>Category</th><th>Total</th><th>Distribution</th><th>%</th></tr></thead>
      <tbody>{summary_rows}</tbody>
    </table>
    <div class="grand-total">Grand Total: ${grand_total:.2f}</div>
  </div>

  <div class="card">
    <h2>All Expenses</h2>
    <table>
      <thead><tr><th>Date</th><th>Category</th><th>Amount</th><th>Description</th><th></th></tr></thead>
      <tbody>{expense_rows}</tbody>
    </table>
  </div>
</div>
</body>
</html>"""


class ExpenseHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        expenses = load_expenses()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(build_html(expenses).encode())

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()
        params = urllib.parse.parse_qs(body)
        expenses = load_expenses()
        message = ""

        if self.path == "/add":
            amount_str = params.get("amount", [""])[0]
            category = params.get("category", [""])[0]
            description = params.get("description", [""])[0]
            date = params.get("date", [""])[0]

            if amount_str and category and description and date:
                try:
                    amount = round(float(amount_str), 2)
                    if amount > 0 and category in CATEGORIES:
                        expenses.append({
                            "id": uuid.uuid4().hex[:8],
                            "date": date,
                            "category": category,
                            "amount": amount,
                            "description": description,
                        })
                        save_expenses(expenses)
                        message = f"Added ${amount:.2f} for {description} ({category})"
                except ValueError:
                    message = "Invalid amount."

        elif self.path == "/delete":
            exp_id = params.get("id", [""])[0]
            before = len(expenses)
            expenses = [e for e in expenses if e["id"] != exp_id]
            if len(expenses) < before:
                save_expenses(expenses)
                message = "Expense deleted."

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(build_html(expenses, message).encode())


def main():
    server = http.server.HTTPServer(("localhost", PORT), ExpenseHandler)
    url = f"http://localhost:{PORT}"
    print(f"Expense Tracker running at {url}")
    print("Press Ctrl+C to stop.")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
