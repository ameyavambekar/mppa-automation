import re

import allure

from config import ADMIN_BASE
from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage

ADMIN_DISTRICT_BREAKUP_URL = f"{ADMIN_BASE}/reports/district_breakup.php"


class AdminDistrictBreakupPage(BasePage):
    """Admin — District breakup report (/module/admin/reports/district_breakup.php), Reports › District
    breakup.

    A static report of submitted (paid) applications by district: the page header (``.adm-page-title`` —
    heading and the ``.pg-date`` clock "DD Mon YYYY · HH:MM"), then two cards (``.rep-card``):

    * "Registrations by District / City" — subtitle (``.rep-hdr-sub``) "Grouped by Part A city field — N
      location(s), T total registrations" and one bar row per district (``.dbar-row``: ``.dbar-lbl``
      "<District>, <Division>", ``.dbar-fill`` whose inline width is the count relative to the highest,
      ``.dbar-val`` the count), highest count first.
    * "Detailed Breakup" — ``table.stbl``: District, Division, Total, then Approved / Submitted / Rejected /
      Suspended counts as ``span.sb`` badges.

    No filters, links or export.
    """

    HEADING = "District / City-wise Breakup"
    CHART_CARD = "Registrations by District / City"
    TABLE_CARD = "Detailed Breakup"
    COLUMNS = ("District", "Division", "Total", "Approved", "Submitted", "Rejected", "Suspended")
    STATUS_COLUMNS = ("approved", "submitted", "rejected", "suspended")
    SUMMARY_PATTERN = re.compile(r"^Grouped by .+ — (\d+) location\(s\), (\d+) total registrations$")
    CLOCK_FORMAT = "%d %b %Y · %H:%M"

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("#adm-main .adm-page-title span").first

    @property
    def page_clock(self):
        # "04 Nov 2026 · 05:28"
        return self.page.locator("#adm-main .adm-page-title .pg-date")

    # ── Cards ─────────────────────────────────────────────────────────────────

    @property
    def cards(self):
        return self.page.locator("#adm-main .rep-card")

    def card(self, title: str):
        return self.cards.filter(has=self.page.locator(".rep-hdr-title", has_text=title))

    def card_title(self, title: str):
        return self.card(title).locator(".rep-hdr-title")

    @property
    def summary(self):
        """The bar chart card's subtitle: "Grouped by … — N location(s), T total registrations"."""
        return self.card(self.CHART_CARD).locator(".rep-hdr-sub")

    @property
    def bar_rows(self):
        return self.card(self.CHART_CARD).locator(".dbar-row")

    @property
    def bar_labels(self):
        return self.bar_rows.locator(".dbar-lbl")

    @property
    def table_headers(self):
        return self.card(self.TABLE_CARD).locator("table.stbl thead th")

    @property
    def table_rows(self):
        return self.card(self.TABLE_CARD).locator("table.stbl tbody tr")

    def table_row(self, district: str):
        return self.table_rows.filter(has=self.page.locator("td:first-child", has_text=re.compile(
            rf"^{re.escape(district)}$")))

    # ── Reading ───────────────────────────────────────────────────────────────

    def summary_counts(self) -> tuple[int, int] | None:
        """(N locations, T registrations) from the subtitle, or None when it does not match."""
        match = self.SUMMARY_PATTERN.match(self.summary.inner_text().strip())
        return (int(match.group(1)), int(match.group(2))) if match else None

    def bars_data(self) -> list[dict]:
        """Every bar row: label, district, division (the label split at the first ", "), count and width
        (the inline width in %, or None)."""
        rows = self.bar_rows.evaluate_all("""rows => rows.map(r => ({
            label: r.querySelector('.dbar-lbl').textContent.trim(),
            count: r.querySelector('.dbar-val').textContent.trim(),
            width: r.querySelector('.dbar-fill').style.width}))""")
        for row in rows:
            row["district"], _, row["division"] = row["label"].partition(", ")
            row["count"] = int(row["count"])
            row["width"] = float(row["width"].rstrip("%")) if row["width"].endswith("%") else None
        return rows

    def table_data(self) -> list[dict]:
        """Every table row: district, division and the int counts total, approved, submitted, rejected,
        suspended."""
        rows = self.table_rows.evaluate_all("""rows => rows.map(r =>
            [...r.cells].map(c => c.textContent.replace(/\\s+/g, ' ').trim()))""")
        keys = ("district", "division", "total") + self.STATUS_COLUMNS
        data = []
        for cells in rows:
            row = dict(zip(keys, cells))
            for key in keys[2:]:
                row[key] = int(row[key])
            data.append(row)
        return data

    def table_by_district(self) -> dict[str, dict]:
        return {row["district"]: row for row in self.table_data()}

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open District breakup")
    def open(self):
        self.navigate(ADMIN_DISTRICT_BREAKUP_URL)

    @allure.step("Reload District breakup")
    def reload(self):
        self.page.reload(wait_until="domcontentloaded")
