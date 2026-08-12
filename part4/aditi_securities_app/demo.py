# Aditi Rai - Part IV live-cloud retrain demo driver.
# Uses Flask's test client (no need for a running HTTP server or a GUI
# browser) to exercise the real app routes against the live Azure MySQL
# database, demonstrating: quote #1 -> new price data arrives -> forced
# retrain -> quote #2 returns a different, model-driven result -> the
# portfolio risk view and quote log both reflect the live write.
#
# Run with DATABASE_URL pointed at the Azure MySQL server (see db.py):
#   export DATABASE_URL="mysql+pymysql://<user>:<password>@<azure-host>:3306/aditi_securities"
#   python3 demo.py
#
# Real output from running this against aditi-securities-mysql.mysql.database.azure.com
# is captured verbatim in cloud_demo_output.txt.

import re
from app import app

client = app.test_client()

print("=== GET / ===")
r = client.get("/")
print("status:", r.status_code)
m = re.search(r'Current deployed model version: <span class="mono">([^<]*)</span>', r.get_data(as_text=True))
print("model version shown:", m.group(1) if m else None)

print("\n=== POST /quote (AAPL) - quote #1, before new data ===")
r = client.post("/quote", data={"name": "Jordan Reyes", "risk_tolerance": "Moderate", "ticker": "AAPL"})
html = r.get_data(as_text=True)
for pat in [r'Quote #(\d+) for (\w+)', r'(\d+\.\d)%\s*</span>\s*<span class="muted">\(as of ([\d-]+)\)', r'Model version: <span class="mono">([^<]+)</span>']:
    mm = re.search(pat, html)
    print(pat, "->", mm.groups() if mm else None)

print("\n=== appending simulated new AAPL price row (2026-07-16) ===")
with open("datalake/raw/prices/AAPL_daily_2026-04-17_2026-07-15.csv") as f:
    lines = f.readlines()
header, rest = lines[0], lines[1:]
new_row = "2026-07-16,323.00,324.50,316.20,318.40,318.40,52000000\n"
with open("datalake/raw/prices/AAPL_daily_2026-04-17_2026-07-15.csv", "w") as f:
    f.write(header)
    f.write(new_row)
    f.writelines(rest)
print("appended:", new_row.strip())

print("\n=== POST /admin/retrain (force) ===")
r = client.post("/admin/retrain", follow_redirects=True)
html = r.get_data(as_text=True)
m = re.search(r'Retrain complete\. ([^<]+)', html)
print("flash message:", m.group(1) if m else None)

print("\n=== POST /quote (AAPL) - quote #2, after retrain ===")
r = client.post("/quote", data={"name": "Jordan Reyes", "risk_tolerance": "Moderate", "ticker": "AAPL"})
html = r.get_data(as_text=True)
for pat in [r'Quote #(\d+) for (\w+)', r'(\d+\.\d)%\s*</span>\s*<span class="muted">\(as of ([\d-]+)\)', r'Model version: <span class="mono">([^<]+)</span>', r'<p>([^<]*probability[^<]*)</p>']:
    mm = re.search(pat, html)
    print(pat, "->", mm.groups() if mm else None)

print("\n=== GET /portfolio/1 ===")
r = client.get("/portfolio/1")
html = r.get_data(as_text=True)
rows = re.findall(r'<td>(\w+)</td>\s*<td>([\d.]+)</td>\s*<td>\$([\d.]+)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td>([^<]*)</td>\s*<td class="mono">([^<]*)</td>', html)
for row in rows:
    print(row)

print("\n=== GET /quotes ===")
r = client.get("/quotes")
html = r.get_data(as_text=True)
rows = re.findall(r'<td>(\d+)</td>\s*<td>([\d\- :]+)</td>\s*<td>([^<]*)</td>\s*<td>(\w+)</td>\s*<td>(\w+)</td>\s*<td>([^<]*)</td>\s*<td class="mono">([^<]*)</td>', html)
for row in rows:
    print(row)
