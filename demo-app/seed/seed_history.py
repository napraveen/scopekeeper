"""Deterministic generator for the `demo-app/acme-portal` repository and git history.

Generates a self-contained Vite + React + TypeScript + Tailwind + Vitest web app
with ~40 backdated commits between August 1 and October 28, 2026 by three fictional
developers, 8 feature-branch merge commits carrying `Effort-Hours:` trailers,
the planted Safari date parsing bug (`ASK-0007`), unwired dark theme tokens (`ASK-0008`),
CSV-only export (`ASK-0009`), the `seed-v1` tag, and a `pre-push` hook protecting `main`.
"""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEVELOPERS: dict[str, tuple[str, str]] = {
    "aisha": ("Aisha Khan", "aisha@pixelandco.dev"),
    "rohan": ("Rohan Verma", "rohan@pixelandco.dev"),
    "meera": ("Meera Nair", "meera@pixelandco.dev"),
}


@dataclass(frozen=True)
class CommitStep:
    """Single backdated file change and commit on a branch."""

    dev: str
    date_iso: str
    message: str
    files: dict[str, str]


@dataclass(frozen=True)
class FeatureBranchSpec:
    """Feature branch with commits and a `--no-ff` merge commit carrying `Effort-Hours:`."""

    branch: str
    title: str
    effort_hours: int
    merge_dev: str
    merge_date_iso: str
    commits: list[CommitStep]


PACKAGE_JSON = """\
{
  "name": "acme-portal",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.49",
    "tailwindcss": "^3.4.15",
    "typescript": "~5.6.2",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
"""

TSCONFIG_JSON = """\
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true
  },
  "include": ["src"]
}
"""

VITE_CONFIG_TS = """\
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "./",
});
"""

TAILWIND_CONFIG_JS = """\
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {},
  },
  plugins: [],
};
"""

INDEX_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Acme Customer Portal</title>
  </head>
  <body class="bg-slate-50 text-slate-900 antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

TOKENS_CSS = """\
:root {
  --bg-surface: #f8fafc;
  --bg-card: #ffffff;
  --text-primary: #0f172a;
  --text-muted: #475569;
  --border-subtle: #e2e8f0;
  --brand-accent: #2563eb;
}

/* Dark theme tokens exist for Clause 2.4 (ASK-0008), but dark mode toggle is not wired yet */
[data-theme="dark"] {
  --bg-surface: #0b0d10;
  --bg-card: #12151a;
  --text-primary: #eceef2;
  --text-muted: #9aa1ad;
  --border-subtle: #1f242d;
  --brand-accent: #3b82f6;
}
"""

SESSION_TS = """\
/**
 * Session utilities for Acme Customer Portal.
 *
 * NOTE: `DEFAULT_SESSION_EXPIRY` intentionally uses the non-ISO space-separated
 * string `'2026-11-04 10:00'` which triggers the planted Safari bug (`ASK-0007`).
 * Safari's strict Date parser rejects `'YYYY-MM-DD HH:mm'` without `'T'`, returning
 * `Invalid Date` (`NaN`) and disabling the login button on Safari.
 * Fixing `DEFAULT_SESSION_EXPIRY` to `'2026-11-04T10:00:00Z'` or normalizing `' '` -> `'T'`
 * resolves the defect.
 */
export const DEFAULT_SESSION_EXPIRY = "2026-11-04 10:00";

export function parseSessionExpiry(expiryInput: string = DEFAULT_SESSION_EXPIRY): Date {
  // Strict Safari simulation: space-separated date strings without 'T' fail in WebKit/Safari
  if (/^\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}/.test(expiryInput)) {
    return new Date(NaN);
  }
  return new Date(expiryInput);
}

export function isSessionActive(
  expiryInput: string = DEFAULT_SESSION_EXPIRY,
  nowMs: number = Date.parse("2026-11-04T08:00:00Z")
): boolean {
  const parsed = parseSessionExpiry(expiryInput);
  if (Number.isNaN(parsed.getTime())) {
    return false;
  }
  return parsed.getTime() > nowMs;
}
"""

LOGIN_TSX = """\
import React, { useState } from "react";
import { DEFAULT_SESSION_EXPIRY, isSessionActive } from "../utils/session";

export interface LoginProps {
  onLoginSuccess: (email: string) => void;
}

export const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState("sam@acme.example");
  const [password, setPassword] = useState("");

  // Planted Safari bug (ASK-0007): checks session expiry with new Date('2026-11-04 10:00')
  const rawSafariCheck = new Date("2026-11-04 10:00");
  const sessionValid = isSessionActive(DEFAULT_SESSION_EXPIRY) && !Number.isNaN(rawSafariCheck.getTime());

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (sessionValid && email.trim()) {
      onLoginSuccess(email.trim());
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-xl bg-white p-6 shadow-sm border border-slate-200"
      >
        <h1 className="text-xl font-semibold text-slate-900 mb-2">Acme Customer Portal</h1>
        <p className="text-sm text-slate-600 mb-6">Sign in to view your reports and account settings.</p>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Work Email
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <label className="block text-sm font-medium text-slate-700 mt-4 mb-4">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          />
        </label>
        <button
          type="submit"
          disabled={!sessionValid}
          className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          Sign in
        </button>
      </form>
    </div>
  );
};
"""

LOGIN_TEST_TS = """\
import { describe, expect, it } from "vitest";
import { DEFAULT_SESSION_EXPIRY, isSessionActive } from "../utils/session";

describe("Safari session expiry check (ASK-0007)", () => {
  it("requires an ISO-8601 session expiry string so Safari enables the login button", () => {
    // Fails before fixing DEFAULT_SESSION_EXPIRY ('2026-11-04 10:00') to ISO ('2026-11-04T10:00:00Z')
    expect(isSessionActive(DEFAULT_SESSION_EXPIRY)).toBe(true);
  });
});
"""

HOME_TSX = """\
import React from "react";

export const Home: React.FC = () => {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Portal Overview</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium uppercase text-slate-500">Active Orders</div>
          <div className="mt-1 text-2xl font-bold text-slate-900">42</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium uppercase text-slate-500">On-Time Shipment</div>
          <div className="mt-1 text-2xl font-bold text-emerald-600">98.4%</div>
        </div>
        <div className="rounded-lg border border-slate-200 bg-white p-4">
          <div className="text-xs font-medium uppercase text-slate-500">Open Inquiries</div>
          <div className="mt-1 text-2xl font-bold text-amber-600">3</div>
        </div>
      </div>
    </section>
  );
};
"""

REPORTS_TSX = """\
import React, { useState } from "react";

export interface ReportRow {
  id: string;
  date: string;
  region: string;
  status: "Delivered" | "Processing" | "Pending";
  totalUsd: number;
}

const SAMPLE_ROWS: ReportRow[] = [
  { id: "ORD-1001", date: "2026-10-14", region: "North", status: "Delivered", totalUsd: 4200 },
  { id: "ORD-1002", date: "2026-10-18", region: "West", status: "Processing", totalUsd: 1850 },
  { id: "ORD-1003", date: "2026-10-25", region: "East", status: "Delivered", totalUsd: 9100 },
];

export function exportReportsCsv(rows: ReportRow[]): string {
  const header = "id,date,region,status,total_usd";
  const body = rows.map((r) => `${r.id},${r.date},${r.region},${r.status},${r.totalUsd}`).join("\\n");
  return `${header}\\n${body}\\n`;
}

export const Reports: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const filtered = SAMPLE_ROWS.filter(
    (r) => statusFilter === "ALL" || r.status === statusFilter
  );

  return (
    <section className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-900">Reports (Filters v1 & CSV Export)</h2>
        <div className="flex items-center gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded border border-slate-300 px-2.5 py-1.5 text-sm"
          >
            <option value="ALL">All Statuses</option>
            <option value="Delivered">Delivered</option>
            <option value="Processing">Processing</option>
            <option value="Pending">Pending</option>
          </select>
          <button
            type="button"
            onClick={() => exportReportsCsv(filtered)}
            className="rounded bg-slate-900 px-3 py-1.5 text-xs font-medium text-white"
          >
            Export CSV
          </button>
        </div>
      </div>
      <table className="min-w-full divide-y divide-slate-200 rounded-lg border border-slate-200 bg-white text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Order ID</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Date</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Region</th>
            <th className="px-4 py-2 text-left font-medium text-slate-600">Status</th>
            <th className="px-4 py-2 text-right font-medium text-slate-600">Amount (USD)</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {filtered.map((row) => (
            <tr key={row.id}>
              <td className="px-4 py-2 font-mono">{row.id}</td>
              <td className="px-4 py-2">{row.date}</td>
              <td className="px-4 py-2">{row.region}</td>
              <td className="px-4 py-2">{row.status}</td>
              <td className="px-4 py-2 text-right">${row.totalUsd.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
};
"""

SETTINGS_TSX = """\
import React from "react";

export const Settings: React.FC = () => {
  // Note: Dark mode toggle is not wired yet (ASK-0008 / SOW 2.4)
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Account Settings</h2>
      <div className="rounded-lg border border-slate-200 bg-white p-4 space-y-3">
        <div>
          <div className="text-sm font-medium text-slate-800">Notification Channel</div>
          <div className="text-xs text-slate-500">Email notifications only (per DEC-002).</div>
        </div>
        <div>
          <div className="text-sm font-medium text-slate-800">Theme</div>
          <div className="text-xs text-slate-500">Light theme active (dark theme tokens pending wiring).</div>
        </div>
      </div>
    </section>
  );
};
"""

ADMIN_USERS_TSX = """\
import React from "react";

export const AdminUsers: React.FC = () => {
  return (
    <section className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-900">Admin Users (I7)</h2>
      <p className="text-sm text-slate-600">Manage Acme portal user roles and invitations.</p>
    </section>
  );
};
"""

APP_TSX = """\
import React, { useState } from "react";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Reports } from "./pages/Reports";
import { Settings } from "./pages/Settings";
import { AdminUsers } from "./pages/AdminUsers";

export const App: React.FC = () => {
  const [userEmail, setUserEmail] = useState<string | null>("sam@acme.example");
  const [tab, setTab] = useState<"home" | "reports" | "admin" | "settings">("home");

  if (!userEmail) {
    return <Login onLoginSuccess={setUserEmail} />;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <span className="font-semibold text-slate-900">Acme Portal</span>
          <nav className="flex gap-4 text-sm">
            <button onClick={() => setTab("home")} className="hover:text-blue-600">Home</button>
            <button onClick={() => setTab("reports")} className="hover:text-blue-600">Reports</button>
            <button onClick={() => setTab("admin")} className="hover:text-blue-600">Admin Users</button>
            <button onClick={() => setTab("settings")} className="hover:text-blue-600">Settings</button>
          </nav>
        </div>
        <button
          onClick={() => setUserEmail(null)}
          className="text-xs text-slate-500 hover:text-slate-800"
        >
          Sign out ({userEmail})
        </button>
      </header>
      <main className="mx-auto max-w-5xl p-6">
        {tab === "home" && <Home />}
        {tab === "reports" && <Reports />}
        {tab === "admin" && <AdminUsers />}
        {tab === "settings" && <Settings />}
      </main>
    </div>
  );
};
"""

MAIN_TSX = """\
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./theme/tokens.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
"""

PRE_PUSH_HOOK = """\
#!/usr/bin/env sh
# Reject direct pushes to main (Builder must push only to sk/ask-NNNN-<slug> branches)
while read local_ref local_sha remote_ref remote_sha; do
  if [ "$remote_ref" = "refs/heads/main" ]; then
    echo "ERROR: Direct pushes to main are forbidden by ScopeKeeper policy. Use a sk/ask-NNNN-<slug> branch." >&2
    exit 1
  fi
done
exit 0
"""


def _build_feature_specs() -> list[FeatureBranchSpec]:
    """Return the 8 feature branches with ~4 commits each + merge commit (41 commits total)."""
    return [
        FeatureBranchSpec(
            branch="feat/responsive-layout",
            title="Responsive layout (I1)",
            effort_hours=30,
            merge_dev="aisha",
            merge_date_iso="2026-08-14T17:30:00+05:30",
            commits=[
                CommitStep(
                    "aisha",
                    "2026-08-03T11:00:00+05:30",
                    "feat(layout): add Vite + TypeScript + Tailwind config",
                    {
                        "tsconfig.json": TSCONFIG_JSON,
                        "vite.config.ts": VITE_CONFIG_TS,
                        "tailwind.config.js": TAILWIND_CONFIG_JS,
                    },
                ),
                CommitStep(
                    "rohan",
                    "2026-08-06T14:20:00+05:30",
                    "feat(layout): create responsive shell and index.html",
                    {"index.html": INDEX_HTML},
                ),
                CommitStep(
                    "meera",
                    "2026-08-10T16:05:00+05:30",
                    "feat(layout): add Home overview cards",
                    {"src/pages/Home.tsx": HOME_TSX},
                ),
                CommitStep(
                    "aisha",
                    "2026-08-13T18:10:00+05:30",
                    "feat(layout): wire mobile-friendly navigation bar",
                    {"src/docs/layout-notes.md": "# Responsive Layout (I1)\nVerified on Chrome, Firefox, Edge, Safari.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/login",
            title="Login (I2)",
            effort_hours=16,
            merge_dev="rohan",
            merge_date_iso="2026-08-25T16:45:00+05:30",
            commits=[
                CommitStep(
                    "rohan",
                    "2026-08-17T10:30:00+05:30",
                    "feat(auth): add session expiry helper",
                    {"src/utils/session.ts": SESSION_TS},
                ),
                CommitStep(
                    "rohan",
                    "2026-08-20T15:00:00+05:30",
                    "feat(auth): build Login form component",
                    {"src/pages/Login.tsx": LOGIN_TSX},
                ),
                CommitStep(
                    "meera",
                    "2026-08-22T12:15:00+05:30",
                    "test(auth): add Vitest session expiry unit test",
                    {"src/__tests__/login.test.ts": LOGIN_TEST_TS},
                ),
                CommitStep(
                    "rohan",
                    "2026-08-24T17:40:00+05:30",
                    "docs(auth): document session timeout behavior",
                    {"src/docs/auth-notes.md": "# Login & Session (I2)\nSession check uses DEFAULT_SESSION_EXPIRY.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/reports-v1",
            title="Reports v1 (I3)",
            effort_hours=40,
            merge_dev="meera",
            merge_date_iso="2026-09-08T18:00:00+05:30",
            commits=[
                CommitStep(
                    "meera",
                    "2026-08-28T11:15:00+05:30",
                    "feat(reports): add initial order report table",
                    {"src/pages/Reports.tsx": REPORTS_TSX},
                ),
                CommitStep(
                    "aisha",
                    "2026-09-01T14:50:00+05:30",
                    "feat(reports): add status filter dropdown (v1)",
                    {"src/docs/reports-v1.md": "# Reports v1 (I3)\nStatus filter and tabular summary.\n"},
                ),
                CommitStep(
                    "meera",
                    "2026-09-04T16:30:00+05:30",
                    "perf(reports): memoize filtered report rows",
                    {"src/docs/reports-perf.md": "# Reports Table Rendering\nIn-memory dataset for sub-second filtering.\n"},
                ),
                CommitStep(
                    "rohan",
                    "2026-09-07T15:10:00+05:30",
                    "test(reports): verify status filter counts",
                    {"src/docs/reports-qa.md": "# Reports v1 QA\nVerified Delivered/Processing/Pending filters.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/reports-v2",
            title="Reports v2 (CR-001)",
            effort_hours=61,
            merge_dev="aisha",
            merge_date_iso="2026-09-21T17:15:00+05:30",
            commits=[
                CommitStep(
                    "aisha",
                    "2026-09-11T10:40:00+05:30",
                    "feat(reports-v2): add multi-region breakdown schema",
                    {"src/docs/reports-v2-schema.md": "# Reports v2 Schema\nMulti-region aggregation columns.\n"},
                ),
                CommitStep(
                    "meera",
                    "2026-09-14T13:20:00+05:30",
                    "feat(reports-v2): add quarterly rollup calculations",
                    {"src/docs/reports-v2-rollup.md": "# Quarterly Rollup\nAggregates order totals by region.\n"},
                ),
                CommitStep(
                    "rohan",
                    "2026-09-17T16:45:00+05:30",
                    "feat(reports-v2): add comparison summary header",
                    {"src/docs/reports-v2-ui.md": "# Comparison Header\nPeriod-over-period variance badges.\n"},
                ),
                CommitStep(
                    "aisha",
                    "2026-09-20T18:05:00+05:30",
                    "test(reports-v2): add rollup edge-case fixtures",
                    {"src/docs/reports-v2-tests.md": "# Reports v2 Tests\nEmpty region and zero-dollar order cases.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/auth-refresh",
            title="Auth refresh (I5)",
            effort_hours=18,
            merge_dev="rohan",
            merge_date_iso="2026-09-30T16:00:00+05:30",
            commits=[
                CommitStep(
                    "rohan",
                    "2026-09-23T11:30:00+05:30",
                    "feat(auth): add silent token refresh scheduler",
                    {"src/docs/auth-refresh.md": "# Auth Refresh (I5)\nRefreshes bearer token 5m before expiry.\n"},
                ),
                CommitStep(
                    "aisha",
                    "2026-09-25T15:15:00+05:30",
                    "feat(auth): handle 401 retry queue",
                    {"src/docs/auth-retry.md": "# 401 Retry Queue\nQueues concurrent requests during token refresh.\n"},
                ),
                CommitStep(
                    "rohan",
                    "2026-09-28T14:00:00+05:30",
                    "fix(auth): clear stale session storage on sign-out",
                    {"src/docs/auth-signout.md": "# Sign-out Cleanup\nClears session cache on explicit logout.\n"},
                ),
                CommitStep(
                    "meera",
                    "2026-09-29T17:20:00+05:30",
                    "test(auth): cover token refresh backoff",
                    {"src/docs/auth-refresh-tests.md": "# Auth Refresh Tests\nSimulated clock backoff assertions.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/admin-users",
            title="Admin users page (I7)",
            effort_hours=52,
            merge_dev="meera",
            merge_date_iso="2026-10-12T17:50:00+05:30",
            commits=[
                CommitStep(
                    "meera",
                    "2026-10-02T10:15:00+05:30",
                    "feat(admin): scaffold AdminUsers directory view",
                    {"src/pages/AdminUsers.tsx": ADMIN_USERS_TSX},
                ),
                CommitStep(
                    "aisha",
                    "2026-10-05T14:40:00+05:30",
                    "feat(admin): add role assignment modal",
                    {"src/docs/admin-roles.md": "# Admin Roles (I7)\nViewer, Analyst, and Billing Admin roles.\n"},
                ),
                CommitStep(
                    "rohan",
                    "2026-10-08T16:10:00+05:30",
                    "feat(admin): add user invite audit log",
                    {"src/docs/admin-audit.md": "# Invite Audit Log\nTracks inviter and timestamp.\n"},
                ),
                CommitStep(
                    "meera",
                    "2026-10-11T15:30:00+05:30",
                    "test(admin): verify permission guard on role edits",
                    {"src/docs/admin-tests.md": "# Admin Users QA\nRole guard tests.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/theme-tokens",
            title="Theme tokens (I6)",
            effort_hours=14,
            merge_dev="aisha",
            merge_date_iso="2026-10-20T16:30:00+05:30",
            commits=[
                CommitStep(
                    "aisha",
                    "2026-10-14T11:00:00+05:30",
                    "feat(theme): add light and dark CSS custom property tokens",
                    {"src/theme/tokens.css": TOKENS_CSS},
                ),
                CommitStep(
                    "meera",
                    "2026-10-16T14:25:00+05:30",
                    "feat(settings): add Settings page with theme status note",
                    {"src/pages/Settings.tsx": SETTINGS_TSX},
                ),
                CommitStep(
                    "aisha",
                    "2026-10-18T16:00:00+05:30",
                    "style(theme): apply surface and text token variables",
                    {"src/docs/theme-tokens.md": "# Theme Tokens (I6)\nLight and dark palette tokens defined; dark toggle unwired.\n"},
                ),
                CommitStep(
                    "rohan",
                    "2026-10-19T17:15:00+05:30",
                    "docs(theme): document Clause 2.4 token mapping",
                    {"src/docs/theme-clause-2-4.md": "# Clause 2.4\nDark mode wiring tracked separately.\n"},
                ),
            ],
        ),
        FeatureBranchSpec(
            branch="feat/csv-export",
            title="CSV export (I8)",
            effort_hours=12,
            merge_dev="rohan",
            merge_date_iso="2026-10-28T17:00:00+05:30",
            commits=[
                CommitStep(
                    "rohan",
                    "2026-10-22T10:50:00+05:30",
                    "feat(csv): implement exportReportsCsv serializer",
                    {"src/docs/csv-export.md": "# CSV Export (I8)\nExports id,date,region,status,total_usd.\n"},
                ),
                CommitStep(
                    "meera",
                    "2026-10-24T13:45:00+05:30",
                    "feat(app): assemble top-level App and main entrypoint",
                    {"src/App.tsx": APP_TSX, "src/main.tsx": MAIN_TSX},
                ),
                CommitStep(
                    "aisha",
                    "2026-10-26T15:30:00+05:30",
                    "test(csv): verify header and row formatting",
                    {"src/docs/csv-tests.md": "# CSV Export Tests\nVerified UTF-8 CSV output.\n"},
                ),
                CommitStep(
                    "rohan",
                    "2026-10-27T18:00:00+05:30",
                    "chore(release): prepare Milestone 1 release notes",
                    {"README.md": "# Acme Customer Portal\n\nBuilt by Pixel & Co for Acme Inc.\n"},
                ),
            ],
        ),
    ]


def _run_git(
    repo_dir: Path,
    args: list[str],
    *,
    dev: str = "aisha",
    date_iso: str = "2026-08-01T10:00:00+05:30",
) -> None:
    name, email = DEVELOPERS[dev]
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": name,
            "GIT_AUTHOR_EMAIL": email,
            "GIT_AUTHOR_DATE": date_iso,
            "GIT_COMMITTER_NAME": name,
            "GIT_COMMITTER_EMAIL": email,
            "GIT_COMMITTER_DATE": date_iso,
        }
    )
    subprocess.run(
        ["git", *args],
        cwd=str(repo_dir),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def _force_remove_dir(target: Path) -> None:
    """Remove a directory tree even if `.git/objects` files are read-only on Windows."""
    if not target.exists():
        return

    def _onerror(func: object, path: str, _exc_info: object) -> None:
        os.chmod(path, stat.S_IWRITE)
        if callable(func):
            func(path)

    shutil.rmtree(target, onerror=_onerror)


def generate_acme_portal(target_dir: Path) -> dict[str, int]:
    """Generate `demo-app/acme-portal` from scratch with deterministic git history."""
    _force_remove_dir(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    _run_git(target_dir, ["init", "-b", "main"])
    _run_git(target_dir, ["config", "user.name", DEVELOPERS["aisha"][0]])
    _run_git(target_dir, ["config", "user.email", DEVELOPERS["aisha"][1]])
    _run_git(target_dir, ["config", "commit.gpgsign", "false"])

    # Initial commit on main (August 1, 2026)
    (target_dir / "package.json").write_text(PACKAGE_JSON, encoding="utf-8")
    (target_dir / ".gitignore").write_text("node_modules/\ndist/\n", encoding="utf-8")
    _run_git(target_dir, ["add", "."], dev="aisha", date_iso="2026-08-01T10:00:00+05:30")
    _run_git(
        target_dir,
        ["commit", "-m", "chore: initialize acme-portal repository"],
        dev="aisha",
        date_iso="2026-08-01T10:00:00+05:30",
    )

    specs = _build_feature_specs()
    for spec in specs:
        first_date = spec.commits[0].date_iso
        _run_git(
            target_dir,
            ["checkout", "-b", spec.branch],
            dev=spec.commits[0].dev,
            date_iso=first_date,
        )
        for step in spec.commits:
            for rel_path, content in step.files.items():
                full_path = target_dir / rel_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")
            _run_git(target_dir, ["add", "."], dev=step.dev, date_iso=step.date_iso)
            _run_git(
                target_dir,
                ["commit", "-m", step.message],
                dev=step.dev,
                date_iso=step.date_iso,
            )

        _run_git(
            target_dir,
            ["checkout", "main"],
            dev=spec.merge_dev,
            date_iso=spec.merge_date_iso,
        )
        merge_msg = (
            f"Merge branch '{spec.branch}': {spec.title}\n\n"
            f"Effort-Hours: {spec.effort_hours}"
        )
        _run_git(
            target_dir,
            ["merge", "--no-ff", spec.branch, "-m", merge_msg],
            dev=spec.merge_dev,
            date_iso=spec.merge_date_iso,
        )
        _run_git(
            target_dir,
            ["branch", "-d", spec.branch],
            dev=spec.merge_dev,
            date_iso=spec.merge_date_iso,
        )

    # Tag the final commit seed-v1
    _run_git(
        target_dir,
        ["tag", "-a", "seed-v1", "-m", "Seed state v1 for ScopeKeeper demo"],
        dev="rohan",
        date_iso="2026-10-28T17:05:00+05:30",
    )

    # Install .git/hooks/pre-push hook rejecting direct pushes to main
    hooks_dir = target_dir / ".git" / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    pre_push_path = hooks_dir / "pre-push"
    pre_push_path.write_text(PRE_PUSH_HOOK, encoding="utf-8", newline="\n")
    pre_push_path.chmod(pre_push_path.stat().st_mode | stat.S_IEXEC)

    commit_count_out = subprocess.run(
        ["git", "rev-list", "--count", "HEAD"],
        cwd=str(target_dir),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    merge_count_out = subprocess.run(
        ["git", "log", "--merges", "--grep=Effort-Hours:", "--oneline"],
        cwd=str(target_dir),
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    merges = [line for line in merge_count_out.splitlines() if line.strip()]

    return {
        "total_commits": int(commit_count_out),
        "effort_merges": len(merges),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    target = Path(
        os.environ.get("DEMO_REPO_PATH", str(repo_root / "demo-app" / "acme-portal"))
    ).resolve()
    stats = generate_acme_portal(target)
    print(
        f"Generated {target} with {stats['total_commits']} commits, "
        f"{stats['effort_merges']} Effort-Hours merges, tag 'seed-v1', and pre-push hook."
    )


if __name__ == "__main__":
    main()
