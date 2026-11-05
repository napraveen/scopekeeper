"""
ScopeKeeper Google Workspace Integration.
Provides 100% free Google Sheets & Google Docs sync for:
1. Live Client Billing & Scope Ledger Sheet (auto-appends confirmed Change Orders)
2. Google Docs Formatted SOW Amendment Generator
3. Google Apps Script Webhook Relay (100% free zero-config webhook sync)
"""

import os
import csv
import json
import httpx
from datetime import datetime, timezone

# Load .env variables automatically if present
_env_path = os.path.join(r"f:\2026 - Projects\scopekeeper", ".env")
if os.path.exists(_env_path):
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                os.environ[_k.strip()] = _v.strip()

GOOGLE_SHEET_WEBHOOK_URL = os.environ.get("GOOGLE_SHEET_WEBHOOK_URL", "")
GW_DIR = os.path.join(r"f:\2026 - Projects\scopekeeper", "contracts", "google_workspace")
DOCS_DIR = os.path.join(GW_DIR, "docs")
os.makedirs(DOCS_DIR, exist_ok=True)

CSV_LEDGER_PATH = os.path.join(GW_DIR, "ScopeKeeper_Master_Billing_Ledger.csv")

def _init_csv_ledger():
    if not os.path.exists(CSV_LEDGER_PATH):
        with open(CSV_LEDGER_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp UTC",
                "Change Order ID",
                "Deliverable Title",
                "Client Organization",
                "Billable Hours",
                "Hourly Rate ($)",
                "Total Value ($)",
                "Contract Status",
                "SOW Governing Clause",
                "Signed Amendment File",
                "GitHub PR URL"
            ])

async def sync_change_order_to_google_sheet(change_order_data: dict, build_res: dict) -> dict:
    """
    Append an authorized Change Order row into Google Sheets.
    If GOOGLE_SHEET_WEBHOOK_URL is set, sends an asynchronous HTTP POST.
    Also updates the local synchronized Master Billing Ledger CSV.
    """
    _init_csv_ledger()
    
    cr_id = change_order_data["id"]
    title = change_order_data["title"]
    hours = change_order_data["hours"]
    rate = change_order_data.get("rate", 90.0)
    cost = change_order_data["cost"]
    clause = change_order_data.get("clause", "Clause 6.1 Change Control")
    amendment_file = build_res.get("amendment_file", f"contracts/amendments/AMENDMENT_{cr_id}.md")
    github_pr_url = build_res.get("github_pr_url", "")
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    row_data = [
        now_iso,
        cr_id,
        title,
        "Acme Corp",
        str(hours),
        f"${rate:.2f}",
        f"${cost:,.2f}",
        "AUTHORIZED & BOUND",
        clause,
        amendment_file,
        github_pr_url
    ]
    
    # 1. Append to local CSV Ledger
    with open(CSV_LEDGER_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(row_data)
        
    synced_webhook = False
    
    # 2. If Google Sheet Webhook configured, POST live row
    if GOOGLE_SHEET_WEBHOOK_URL:
        payload = {
            "timestamp": now_iso,
            "cr_id": cr_id,
            "deliverable": title,
            "client": "Acme Corp",
            "hours": hours,
            "rate": rate,
            "total_value": cost,
            "status": "AUTHORIZED",
            "clause": clause,
            "amendment": amendment_file,
            "pr_url": github_pr_url
        }
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                resp = await client.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload)
                if resp.status_code in [200, 201, 302]:
                    synced_webhook = True
        except Exception as e:
            print(f"[GoogleSheets] Webhook relay notice: {e}")
            
    # 3. Generate Google Docs formatted HTML Document
    doc_html = generate_google_docs_formatted_amendment(change_order_data, build_res)
    
    return {
        "csv_path": CSV_LEDGER_PATH,
        "synced_webhook": synced_webhook,
        "row_added": row_data,
        "doc_file": doc_html
    }

def generate_google_docs_formatted_amendment(change_order_data: dict, build_res: dict) -> str:
    """
    Generate an official Google Docs formatted HTML document ready for Google Drive / Google Docs export.
    """
    cr_id = change_order_data["id"]
    slug = change_order_data["slug"]
    title = change_order_data["title"]
    hours = change_order_data["hours"]
    rate = change_order_data.get("rate", 90.0)
    cost = change_order_data["cost"]
    clause = change_order_data.get("clause", "Clause 6.1 Change Control")
    branch = build_res.get("branch", f"feature/{cr_id.lower()}")
    commit = build_res.get("commit", "8f1a23b")
    audit_digest = build_res.get("audit_digest", "SHA-256 Digest")
    now_iso = datetime.now(timezone.utc).strftime("%B %d, %Y (%H:%M UTC)")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Google Docs — SOW Amendment {cr_id}</title>
  <style>
    body {{
      font-family: 'Roboto', -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      max-width: 800px;
      margin: 40px auto;
      padding: 60px 80px;
      background: #ffffff;
      color: #1f2937;
      line-height: 1.6;
      box-shadow: 0 4px 20px rgba(0,0,0,0.08);
      border-radius: 4px;
    }}
    .doc-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #e5e7eb;
      padding-bottom: 20px;
      margin-bottom: 30px;
    }}
    .badge {{
      background: #e0e7ff;
      color: #3730a3;
      padding: 6px 14px;
      border-radius: 9999px;
      font-weight: 600;
      font-size: 13px;
    }}
    h1 {{ font-size: 24px; color: #111827; margin: 0; }}
    h2 {{ font-size: 16px; color: #4b5563; border-bottom: 1px solid #f3f4f6; padding-bottom: 6px; margin-top: 28px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
    th, td {{ padding: 10px 14px; text-align: left; border-bottom: 1px solid #e5e7eb; font-size: 14px; }}
    th {{ background: #f9fafb; font-weight: 600; color: #374151; }}
    .signature-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-top: 40px; padding-top: 20px; border-top: 1px solid #e5e7eb; }}
    .sig-box {{ background: #f9fafb; padding: 16px; border-radius: 6px; border: 1px solid #e5e7eb; }}
    .audit {{ font-family: monospace; font-size: 11px; color: #6b7280; word-break: break-all; }}
  </style>
</head>
<body>
  <div class="doc-header">
    <div>
      <h1>Statement of Work Amendment ({cr_id})</h1>
      <p style="margin: 4px 0 0 0; color: #6b7280; font-size: 13px;">Acme Web Portal (Governing SOW v1.2)</p>
    </div>
    <div class="badge">EXECUTION COMPLETE</div>
  </div>

  <p><strong>Effective Date:</strong> {now_iso}</p>
  <p>This document formalizes the commercial and engineering inclusion of the deliverable below under <strong>{clause}</strong>.</p>

  <h2>1. Approved Deliverable & Scope</h2>
  <table>
    <tr><th>Change Order ID</th><td><strong>{cr_id}</strong></td></tr>
    <tr><th>Feature Deliverable</th><td><strong>{title}</strong></td></tr>
    <tr><th>Governing Clause</th><td>{clause}</td></tr>
    <tr><th>Git Feature Branch</th><td><code>{branch}</code></td></tr>
    <tr><th>Commit Hash</th><td><code>{commit}</code></td></tr>
  </table>

  <h2>2. Financial Governance & Commercial Terms</h2>
  <table>
    <tr><th>Authorized Effort</th><td><strong>{hours} billable hours</strong></td></tr>
    <tr><th>Governing Agency Rate</th><td>${rate:.2f} / hour</td></tr>
    <tr><th>Total Authorized Cost</th><td><strong style="color: #059669; font-size: 16px;">${cost:,}.00 USD</strong></td></tr>
    <tr><th>Invoicing Schedule</th><td>Direct addition to monthly billing ledger</td></tr>
  </table>

  <h2>3. Digital Execution & Audit Trail</h2>
  <div class="signature-grid">
    <div class="sig-box">
      <strong>Client Representative:</strong><br/>
      Sam (Acme Corp)<br/>
      <small style="color: #059669;">✔ Authorized via Telegram Client Desk</small>
    </div>
    <div class="sig-box">
      <strong>Agency Governance:</strong><br/>
      Priya Sharma / ScopeKeeper Core<br/>
      <small style="color: #059669;">✔ SOW Envelope Bound</small>
    </div>
  </div>

  <p style="margin-top: 30px;"><strong>Cryptographic Audit Digest:</strong></p>
  <p class="audit">{audit_digest}</p>
</body>
</html>
"""
    filename = f"GOOGLE_DOC_AMENDMENT_{cr_id}_{slug}.html"
    filepath = os.path.join(DOCS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_content)
        
    return filepath
