# Statement of Work (SOW) — Acme Web Portal

**Project:** Acme Web Portal  
**Version:** 1.2  
**Effective Date:** August 1, 2026  
**Parties:**  
- **Agency:** Pixel & Co Digital Services Pvt. Ltd. (Mumbai, India)  
- **Client:** Acme Inc. (New York, NY, USA)

---

## 1. Core Web Application & Platform Scope

### Clause 1.1 — Responsive Web Application (Deliverable D1)
Pixel & Co will design, build, and deploy a responsive browser-based web application for the Acme Web Portal.
- **Included:**
  - Desktop and mobile browsers (responsive breakpoints from 360px to 1920px).
  - Support for the latest two stable versions of Google Chrome, Apple Safari, and Mozilla Firefox.
  - User authentication and session login flow (`login`).

### Clause 1.3 — Platform Exclusions (Mobile Applications)
Native mobile applications (including native iOS apps, native Android apps, React Native/Flutter store builds, and Apple App Store or Google Play Store submissions) are **explicitly excluded** from this Statement of Work. Any mobile app requirement will be handled as an out-of-scope Change Request under Clause 6.1.

---

## 2. Design System & Theming

### Clause 2.4 — Theming & Brand Identity (Deliverable D2)
The Acme Web Portal interface will implement Acme's visual identity across all application views.
- **Included:**
  - Light theme and dark theme (`light theme`, `dark theme`) with user toggle persistence.
  - Application of official Acme brand colours (`brand colours`).
  - Typography configured with the official Acme brand typeface (`brand typeface`).

---

## 3. Reporting & Data Exports

### Clause 3.2 — Reports Page & Export (Deliverable D3)
Pixel & Co will deliver an interactive Reports page enabling authorized users to inspect operational metrics.
- **Included:**
  - Interactive report filters (`filters`) by date range, status, and category.
  - One-click data export in standard comma-separated values format (`CSV export`).
- **Note:** Native spreadsheet binary formats (e.g., `.xlsx` workbooks with multi-sheet styling or formulas) and formatted PDF report generators are not included in Clause 3.2 unless added via Change Request.

### Clause 3.5 — Third-Party BI Exclusions
Direct connectors, live warehouse syncs, or embedded integrations with third-party Business Intelligence platforms (`Third-party BI integrations`, such as Power BI, Tableau, or Looker) are **explicitly excluded** from this agreement.

---

## 4. Administrative Analytics

### Clause 4.1 — Admin Analytics Dashboard (Deliverable D4)
Pixel & Co will deliver an internal Admin Analytics Dashboard (`Admin analytics dashboard`) summarizing user activity, report usage, and account KPIs for workspace administrators.

---

## 5. Warranty & Defect Resolution

### Clause 5.1 — 30-Day Post-Delivery Warranty
Pixel & Co provides a **30-calendar-day warranty** (`warranty_days: 30`) on each completed plan item starting from its completion date (`done_on`). Any reproducible defect where a delivered item fails to operate as specified in its governing clause within 30 days of `done_on` will be remediated by Pixel & Co **free of charge**. Requests concerning unstarted items or features outside the delivered specification are not defects.

---

## 6. Change Control, Pricing & Scope Swaps

### Clause 6.1 — Change Orders, Rate Card & Feature Swaps
Any request that falls outside the deliverables in Sections 1–4 or contradicts a recorded project decision requires a Change Order before implementation:
1. **Rate Card Pricing:** Out-of-scope work is estimated from the codebase and priced in USD at the blended agency rate of **$45/hour**, adjusted by an estimate confidence contingency (**+5%** for `high` confidence, **+15%** for `medium` confidence, **+25%** for `low` confidence) and rounded half-up to the nearest **$10**.
2. **Equal-Size Scope Swaps:** At the Client's election and subject to Account Manager approval, a new feature may be swapped at **$0 additional cost** in place of one or two **unstarted** in-scope plan items whose total estimated hours are within **±10%** (`tolerance: 0.10`) of the new feature's hours.
3. **Monthly Goodwill Bucket:** Pixel & Co maintains an optional **8 hours/month** goodwill allowance for minor enhancements under **2 hours**, granted at the Account Manager's discretion.
