"""InvoiceService for monthly ledger summaries and CSV invoice exports."""

from __future__ import annotations

from clerk.db.repositories import LedgerRepository
from clerk.domain.models import ScopeMapConfig
from clerk.domain.templates import render_invoice_csv, render_ledger_message


class InvoiceService:
    """Service that formats monthly audit ledgers and downloadable CSV invoices."""

    def __init__(self, repo: LedgerRepository, scope_map: ScopeMapConfig) -> None:
        self._repo = repo
        self._scope_map = scope_map

    def render_ledger_for_month(self, month: str) -> str:
        """Render the human-readable ledger summary for `month` (YYYY-MM)."""
        entries = self._repo.compute_ledger_entries(month=month)
        bucket = float(self._scope_map.change_policy.goodwill_hours_per_month)
        overview = self._repo.compute_overview(month=month, bucket_hours=bucket)
        return render_ledger_message(
            month=month,
            entries=entries,
            revenue_protected_cents=overview.revenue_protected_cents,
            swaps_count=overview.change_orders.swaps,
            goodwill_used=overview.goodwill.used_hours,
            goodwill_bucket=overview.goodwill.bucket_hours,
        )

    def render_csv_for_month(self, month: str) -> str:
        """Render the monthly CSV invoice for `month` (YYYY-MM)."""
        entries = self._repo.compute_ledger_entries(month=month)
        return render_invoice_csv(entries)
