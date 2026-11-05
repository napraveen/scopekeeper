"""
ScopeKeeper Jira Cloud Integration.
Provides 100% free Atlassian Jira issue tracking for:
1. Change Order Stories (logged to sprint backlog upon client confirmation)
2. Defect Warranty Bugs (logged with $0.00 billable tag under Clause 5.1)

Supports both Live Jira Cloud REST API (via JIRA_URL + JIRA_API_TOKEN)
and local deterministic Jira Audit Ticket persistence.
"""

import os
import json
import uuid
import httpx
from datetime import datetime, timezone

# Optional environment configurations
JIRA_URL = os.environ.get("JIRA_URL", "https://scopekeeper.atlassian.net").rstrip("/")
JIRA_EMAIL = os.environ.get("JIRA_EMAIL", "agency-lead@scopekeeper.io")
JIRA_API_TOKEN = os.environ.get("JIRA_API_TOKEN", "")
JIRA_PROJECT_KEY = os.environ.get("JIRA_PROJECT_KEY", "ACME")

JIRA_DIR = os.path.join(r"f:\2026 - Projects\scopekeeper", "contracts", "jira")
os.makedirs(JIRA_DIR, exist_ok=True)

_JIRA_COUNTER = 102
_BUG_COUNTER = 103

def get_next_jira_key(prefix: str = "ACME") -> str:
    global _JIRA_COUNTER
    _JIRA_COUNTER += 1
    return f"{prefix}-{_JIRA_COUNTER}"

def get_next_bug_key(prefix: str = "ACME-BUG") -> str:
    global _BUG_COUNTER
    _BUG_COUNTER += 1
    return f"{prefix}-{_BUG_COUNTER}"

async def create_jira_change_order_story(change_order_data: dict) -> dict:
    """
    Create an official Jira Story for an approved Change Order.
    Logs to Atlassian Jira Cloud if credentials exist, and writes to local Jira ledger.
    """
    cr_id = change_order_data["id"]
    title = change_order_data["title"]
    hours = change_order_data["hours"]
    cost = change_order_data["cost"]
    clause = change_order_data.get("clause", "Clause 6.1 Change Control")
    branch = change_order_data.get("branch", f"feature/{cr_id.lower()}")
    slug = change_order_data.get("slug", "custom-module")
    
    jira_key = get_next_jira_key(JIRA_PROJECT_KEY)
    jira_url = f"{JIRA_URL}/browse/{jira_key}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    summary = f"[{cr_id}] {title}"
    description_text = (
        f"h3. ScopeKeeper Authorized Change Order: {cr_id}\n\n"
        f"* *Deliverable:* {title}\n"
        f"* *Authorized Effort:* {hours} billable hours @ $90/hr\n"
        f"* *Realized Value:* ${cost:,}.00 USD\n"
        f"* *Governing Clause:* {clause}\n"
        f"* *Git Branch:* {branch}\n"
        f"* *Authorized Via:* Acme Client Desk (Telegram @AcmeClientDesk_bot)\n"
        f"* *Status:* Approved & Scheduled for Sprint Implementation\n"
    )
    
    synced_live = False
    
    # Attempt live Jira Cloud REST API call if credentials present
    if JIRA_API_TOKEN and JIRA_EMAIL and "scopekeeper.atlassian.net" not in JIRA_URL:
        endpoint = f"{JIRA_URL}/rest/api/3/issue"
        auth = (JIRA_EMAIL, JIRA_API_TOKEN)
        payload = {
            "fields": {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": summary,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": description_text}]
                        }
                    ]
                },
                "issuetype": {"name": "Story"},
                "labels": ["change-order", "sow-v1.2", "billable", "scopekeeper"]
            }
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(endpoint, json=payload, auth=auth)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    jira_key = data.get("key", jira_key)
                    jira_url = f"{JIRA_URL}/browse/{jira_key}"
                    synced_live = True
        except Exception as e:
            print(f"[Jira] Live API notice: {e}. Falling back to deterministic local Jira audit ticket.")
            
    # Always persist local Jira Ticket record
    ticket_record = {
        "key": jira_key,
        "url": jira_url,
        "issue_type": "Story",
        "summary": summary,
        "cr_id": cr_id,
        "title": title,
        "hours": hours,
        "cost": cost,
        "clause": clause,
        "branch": branch,
        "labels": ["change-order", "sow-v1.2", "billable"],
        "status": "Ready for Dev (Sprint Backlog)",
        "created_at": now_iso,
        "synced_live": synced_live
    }
    
    ticket_file = os.path.join(JIRA_DIR, f"TICKET_{jira_key}_{cr_id}.json")
    with open(ticket_file, "w", encoding="utf-8") as f:
        json.dump(ticket_record, f, indent=2)
        
    return ticket_record

async def create_jira_warranty_defect_bug(defect_text: str, reporter: str = "Client") -> dict:
    """
    Create an official Jira Bug for an in-scope defect covered 100% under Clause 5.1 Warranty ($0.00).
    """
    bug_key = get_next_bug_key("ACME")
    jira_url = f"{JIRA_URL}/browse/{bug_key}"
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    summary = f"[Defect Warranty] {defect_text[:60]}"
    description_text = (
        f"h3. SOW v1.2 Clause 5.1 / Section 4.3 Defect Warranty Triage\n\n"
        f"* *Reported Issue:* \"{defect_text}\"\n"
        f"* *Reporter:* @{reporter} (Telegram Client Desk)\n"
        f"* *Financial Classification:* $0.00 (100% Free under Warranty)\n"
        f"* *SLA:* Immediate P1 Engineering Triage\n"
        f"* *Governing Clause:* Clause 5.1 (30-Day Post-Delivery Warranty)\n"
    )
    
    synced_live = False
    
    # Attempt live Jira Cloud call if credentials present
    if JIRA_API_TOKEN and JIRA_EMAIL and "scopekeeper.atlassian.net" not in JIRA_URL:
        endpoint = f"{JIRA_URL}/rest/api/3/issue"
        auth = (JIRA_EMAIL, JIRA_API_TOKEN)
        payload = {
            "fields": {
                "project": {"key": JIRA_PROJECT_KEY},
                "summary": summary,
                "issuetype": {"name": "Bug"},
                "labels": ["warranty", "clause-5.1", "zero-dollar", "defect-triage"]
            }
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(endpoint, json=payload, auth=auth)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    bug_key = data.get("key", bug_key)
                    jira_url = f"{JIRA_URL}/browse/{bug_key}"
                    synced_live = True
        except Exception:
            pass

    ticket_record = {
        "key": bug_key,
        "url": jira_url,
        "issue_type": "Bug",
        "summary": summary,
        "defect": defect_text,
        "reporter": reporter,
        "cost": 0.0,
        "clause": "Clause 5.1 30-Day Warranty",
        "labels": ["warranty", "clause-5.1", "zero-dollar"],
        "status": "In Triage (P1)",
        "created_at": now_iso,
        "synced_live": synced_live
    }
    
    ticket_file = os.path.join(JIRA_DIR, f"BUG_{bug_key}.json")
    with open(ticket_file, "w", encoding="utf-8") as f:
        json.dump(ticket_record, f, indent=2)
        
    return ticket_record
