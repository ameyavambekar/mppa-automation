import re

import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE

ADMIN_APPEALS_URL = f"{ADMIN_BASE}/appeals/index.php"


class AdminAppealsPage(BasePage):
    """Officer Console — Appeals (/module/admin/appeals/index.php, "Appeals — MPPA Officer Console").

    Header: the three-level route (Order · Registering Authority → Appeal · FORM-III · Divisional Appellate
    Authority → Second Appeal · FORM-IV · Commissionerate) and the view tabs (``a.apl-tab``, ``?view=``, see
    ``VIEWS``) with their counts.

    Appeal views (Awaiting decision / First Appeals / Second Appeals) list one row per appeal: # (appeal id),
    Agency (name + Application ID), District (+ division), Appeal (type badge), Filed, Decision due (badge,
    "N days left"), Hearing, Status (badge) and "Review & decide" (``openAppeal(id)``). Rejected
    applications lists refused applications with their First / Second appeal columns ("Not filed" …).

    "Review & decide" opens ``#aplModal`` (class ``is-open``): the filed appeal as read-only sections
    (``.apm-sec``: h4 title, ``.apl-kv`` boxes of ``small`` label + value — Appellant, Order appealed against,
    Grounds / facts / relief, Limitation, Documents (links), Hearing [, Decision]) and, while the appeal can
    be decided, ``#aplDecide``: one hearing (date / time / mode / venue, "Schedule the hearing") and the
    appellate order (disposal ``#decReason`` + reasons ``#decRemarks``, at least 50 characters, "Save
    appellate order" — confirm()). The page embeds every listed appeal as ``APPEALS`` (id → data).
    """

    VIEWS = {"queue": "Awaiting decision", "first": "First Appeals — Division",
             "second": "Second Appeals — Commissionerate", "rejections": "Rejected applications",
             "hearings": "Hearings & appointments"}
    APPEAL_VIEWS = ("queue", "first", "second")
    EMPTY_VIEW = "No appeals in this list."
    EMPTY_QUEUE = "No appeals are waiting for your decision."
    APPEAL_COLUMNS = ["#", "Agency", "District", "Appeal", "Filed", "Decision due", "Hearing", "Status", ""]
    REJECTION_COLUMNS = ["Agency", "District", "Rejected", "Reason given to the agency", "Appeal (Division)",
                         "Second appeal (Commissionerate)", ""]
    # appellate order (disposal) of a first appeal: value → label
    FIRST_DISPOSALS = {
        "allowed": "Appeal Allowed — Order Set Aside",
        "allowed_conditions": "Appeal Allowed with Conditions",
        "remanded": "Remanded Back for Re-Scrutiny",
        "dismissed_upheld": "Appeal Dismissed — Refusal Upheld",
        "dismissed_default": "Dismissed for Default of Appearance",
        "delay_rejected": "Delay Condonation Rejected",
    }
    # appellate order of a second appeal (the page's DISPOSAL.second, dev 06-Nov-2026): value → label.
    # No "refusal upheld" here — the Commissionerate's dismissal is final (Sec 7(3)).
    SECOND_DISPOSALS = {
        "allowed": "Appeal Allowed — Order Set Aside",
        "allowed_conditions": "Appeal Allowed with Conditions",
        "remanded": "Remanded Back for Re-Scrutiny",
        "dismissed_default": "Dismissed for Default of Appearance",
        "delay_rejected": "Delay Condonation Rejected",
        "final_dismissal": "Final Second Appeal Dismissal",
    }
    HEARING_MODES = ("personal", "virtual")
    SECTIONS = ("1–4 · Appellant", "5 · Order appealed against", "6–8 · Grounds, facts and relief",
                "9 · Limitation", "10 · Documents", "Hearing (one hearing at this level)")

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    # ── Header & tabs ─────────────────────────────────────────────────────────

    @property
    def heading(self):
        return self.page.locator("#adm-main h2").first

    def view_tab(self, view: str):
        """A view tab by its ``?view=`` value (see VIEWS)."""
        return self.page.locator(f"#adm-main a[href='?view={view}']")

    def view_count(self, view: str) -> int:
        label = self.VIEWS[view]
        return int(self.view_tab(view).inner_text().replace(label, "").strip() or 0)

    @property
    def toast(self):
        return self.page.locator("#uiToasts .ui-toast").last

    # ── Lists ─────────────────────────────────────────────────────────────────

    @property
    def table_headers(self):
        return self.page.locator("#adm-main table thead th")

    @property
    def view_rows(self):
        """Rows of the open view (not the empty-view row)."""
        return self.page.locator("#adm-main table tbody tr:not(:has(td[colspan]))")

    @property
    def empty_row(self):
        return self.page.locator("#adm-main table tbody td[colspan]")

    @property
    def main(self):
        """The page body (``#adm-main``). Hearings & appointments has no table: "Upcoming hearings" lists one
        entry per hearing (date, time, mode, "First Appeal #N", agency + Application ID + district + mobile,
        venue, "Open appeal"), then "Past hearings" (dev, 06-Nov-2026)."""
        return self.page.locator("#adm-main")

    def appeal_row(self, appeal_id: int):
        """An appeal view row by its appeal id (the first cell)."""
        return self.view_rows.filter(has=self.page.locator("td:first-child", has_text=re.compile(rf"^\s*{appeal_id}\s*$")))

    def rows_for_application(self, application_id: str):
        return self.view_rows.filter(has=self.page.locator(".ui-mono", has_text=application_id))

    def review_button(self, appeal_id: int):
        return self.appeal_row(appeal_id).get_by_role("button", name="Review & decide")

    def history_link(self, application_id: str):
        """Rejected applications view: the row's History link (the application's processing page)."""
        return self.rows_for_application(application_id).get_by_role("link", name="History")

    # ── Appeal pop-up ─────────────────────────────────────────────────────────

    @property
    def modal(self):
        return self.page.locator("#aplModal")

    @property
    def modal_title(self):
        """'First Appeal (FORM-III) #N — <agency>'."""
        return self.page.locator("#aplTitle")

    @property
    def modal_subtitle(self):
        """'Divisional Appellate Authority, <division> Division · filed yyyy-mm-dd'."""
        return self.page.locator("#aplSub")

    @property
    def modal_chips(self):
        """Type ('First · Division'), Application ID, and 'N days left to decide' (or the result once decided)."""
        return self.page.locator("#aplChips .ui-badge")

    @property
    def modal_close_button(self):
        return self.modal.locator(".apm-x")

    @property
    def modal_body(self):
        return self.page.locator("#aplBody")

    @property
    def modal_sections(self):
        return self.modal_body.locator(".apm-sec")

    def modal_section(self, title: str):
        """A section by its title (see SECTIONS, plus 'Decision' once decided)."""
        return self.modal_sections.filter(has=self.page.locator("h4", has_text=re.compile(rf"^{re.escape(title)}$", re.IGNORECASE)))

    def modal_field(self, label: str):
        """A read-only box by its label, e.g. 'Registration ID', 'Order No.', 'Grounds', 'Filed within time'."""
        return self.modal_body.locator(".apl-kv > div").filter(
            has=self.page.locator("small", has_text=re.compile(rf"^{re.escape(label)}$")))

    @property
    def document_links(self):
        return self.modal_section("10 · Documents").locator("a")

    @property
    def decide_box(self):
        return self.page.locator("#aplDecide")

    @property
    def decide_due(self):
        """'Decide by yyyy-mm-dd — N day(s) left'."""
        return self.decide_box.locator(".apm-due")

    # hearing
    @property
    def hearing_date_input(self):
        return self.page.locator("#hDate")

    @property
    def hearing_time_select(self):
        return self.page.locator("#hTime")

    @property
    def hearing_mode_select(self):
        return self.page.locator("#hMode")

    @property
    def hearing_venue_input(self):
        return self.page.locator("#hVenue")

    @property
    def schedule_hearing_button(self):
        return self.page.locator("#hBtn")

    @property
    def hearing_error(self):
        return self.page.locator("#hErr")

    @property
    def hearing_hint(self):
        return self.page.locator("#hHint")

    # appellate order
    @property
    def disposal_select(self):
        return self.page.locator("#decReason")

    @property
    def disposal_impact(self):
        return self.page.locator("#decImpact")

    @property
    def decision_remarks_textarea(self):
        return self.page.locator("#decRemarks")

    @property
    def decision_remarks_count(self):
        return self.page.locator("#decCount")

    @property
    def save_order_button(self):
        return self.page.locator("#decBtn")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Appeals")
    def open(self):
        self.navigate(ADMIN_APPEALS_URL)
        self.wait_for_load()

    @allure.step("Open the '{view}' appeals view")
    def open_view(self, view: str):
        """view: a key of ``VIEWS``."""
        self.navigate(f"{ADMIN_APPEALS_URL}?view={view}")
        self.wait_for_load()

    @allure.step("Click 'Review & decide' on appeal #{appeal_id}")
    def open_appeal(self, appeal_id: int):
        self.review_button(appeal_id).click()
        self.page.wait_for_function("document.getElementById('aplModal').classList.contains('is-open')")

    @allure.step("Close the appeal")
    def close_appeal(self):
        self.modal_close_button.click()

    @allure.step("Choose the appellate order '{disposal}'")
    def choose_disposal(self, disposal: str):
        """disposal: a FIRST_DISPOSALS value."""
        self.disposal_select.select_option(disposal)

    @allure.step("Write the reasons of the order")
    def fill_reasons(self, text: str):
        self.decision_remarks_textarea.fill(text)

    @allure.step("Click 'Save appellate order' (prompt: {action})")
    def save_order(self, action: str = "accept") -> str:
        """Clicks Save; returns the confirm() text ('' when the page refused before asking). Accepting
        reloads the page once the order is saved."""
        if action != "accept":
            return self.click_and_handle_alert(self.save_order_button, action=action)
        msgs = []
        self.page.once("dialog", lambda d: (msgs.append(d.message), d.accept()))
        try:
            with self.page.expect_navigation(timeout=15000):
                self.save_order_button.click()
        except Exception:
            if msgs:          # the prompt was accepted but the page did not reload
                raise
        self.wait_for_load()
        return msgs[0] if msgs else ""

    @allure.step("Pass the appellate order '{disposal}' on appeal #{appeal_id}")
    def decide(self, appeal_id: int, disposal: str, reasons: str) -> str:
        self.open_appeal(appeal_id)
        self.choose_disposal(disposal)
        self.fill_reasons(reasons)
        return self.save_order("accept")

    @allure.step("Schedule the hearing of appeal #{appeal_id} ({mode}) at {venue}")
    def schedule_hearing(self, appeal_id: int, venue: str, mode: str = "personal") -> str:
        """Opens the appeal and schedules its one hearing on the first date the page offers (the next working
        day) at the first free time slot. Returns the prompt or the page's hearing error ('' when neither
        showed). The caller checks the hearing in ``appeals_data()`` after reopening the view."""
        self.open_appeal(appeal_id)
        date = self.hearing_date_input.input_value()
        self.hearing_date_input.fill(date)
        self.hearing_date_input.dispatch_event("change")
        self.page.wait_for_function(
            "() => { const s = document.getElementById('hTime'); return s && !s.disabled && s.options.length > 1; }")
        slot = self.hearing_time_select.evaluate("s => [...s.options].map(o => o.value).filter(Boolean)[0]")
        self.hearing_time_select.select_option(slot)
        self.hearing_mode_select.select_option(mode)
        self.hearing_venue_input.fill(venue)
        msgs = []
        self.page.once("dialog", lambda d: (msgs.append(d.message), d.accept()))
        try:
            with self.page.expect_navigation(timeout=10000):
                self.schedule_hearing_button.click()
        except Exception:
            pass          # saved in place (no reload) or refused — the caller reads the result
        self.wait_for_load()
        if msgs:
            return msgs[0]
        return self.hearing_error.inner_text().strip() if self.hearing_error.is_visible() else ""

    def appeal_for(self, application_id: str, kind: str = "first") -> dict | None:
        """The ``APPEALS`` entry of ``application_id``'s ``kind`` ("first" / "second") appeal on the open
        view, or None."""
        for appeal in self.appeals_data().values():
            if appeal.get("reg_id") == application_id and appeal.get("type") == kind:
                return appeal
        return None

    # ── Reading (no assertions) ───────────────────────────────────────────────

    def appeals_data(self) -> dict:
        """The page's embedded ``APPEALS`` (appeal id as str → its data)."""
        return self.page.evaluate("() => (typeof APPEALS === 'undefined') ? {} : APPEALS")

    def view_table_data(self) -> list[dict]:
        """Every row of the open view read in one go: agency, application_id (the 13-digit ID in the row)
        and badges (the row's ``.ui-badge`` texts — in the appeal views the type, the decision due and, last,
        the status; in Rejected applications the First / Second appeal columns)."""
        return self.view_rows.evaluate_all("""rows => rows.map(r => {
            const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : '';
            const mono = r.querySelector('.ui-mono');   // the Application ID under the agency name
            const id = (t(mono).match(/\\b\\d{13}\\b/) || r.innerText.match(/\\b\\d{13}\\b/) || [''])[0];
            return {agency: t(r.querySelector('strong') || r.cells[1]), application_id: id,
                    badges: [...r.querySelectorAll('.ui-badge')].map(t)};
        })""")

    def appeal_rows_data(self) -> list[dict]:
        """Appeal view rows as dicts: id, agency, application_id, district, division, type, filed, due,
        hearing, status, button."""
        return self.view_rows.evaluate_all("""rows => rows.map(r => {
            const t = e => e ? e.textContent.replace(/\\s+/g, ' ').trim() : '';
            const c = r.cells;
            return {id: t(c[0]), agency: t(c[1].querySelector('strong')), application_id: t(c[1].querySelector('.ui-mono')),
                    district: t(c[2].firstChild), division: t(c[2].querySelector('.ui-muted')), type: t(c[3]),
                    filed: t(c[4]), due: t(c[5]), hearing: t(c[6]), status: t(c[7]), button: t(c[8])};
        })""")

    def modal_value(self, label: str) -> str:
        """A read-only box's value without its label."""
        return self.modal_field(label).evaluate(
            "e => [...e.childNodes].filter(n => n.nodeName !== 'SMALL').map(n => n.textContent).join('').trim()")

    def editable_fields_in_body(self) -> int:
        """Inputs / selects / textareas inside the filed-appeal sections (the decision box is separate)."""
        return self.modal_body.locator("input, select, textarea, [contenteditable=true]").count()
