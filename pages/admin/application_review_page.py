from datetime import datetime, timedelta, timezone

import allure

from config import ADMIN_BASE
from pages.base_page import BasePage

APPLICATION_REVIEW_URL = f"{ADMIN_BASE}/dashboard/agency_view.php?id={{view_id}}"
IST = timezone(timedelta(hours=5, minutes=30))


class ReviewStage:
    """Where an application stands in the desktop scrutiny loop, as ``AdminApplicationReviewPage.stage()``
    reads it from the page."""
    NEW = "new"                          # nothing reviewed yet
    IN_REVIEW = "in_review"              # some items reviewed / a reply taken into review, no next step yet
    HELD = "held"                        # review saved with an item On Hold — "Send Compliance 1" offered
    WITH_AGENCY = "with_agency"          # Compliance 1 or the window after the hearing — awaiting the agency
    REPLY_RECEIVED = "reply_received"    # the agency replied — "Take reply into review" offered
    SHOW_CAUSE_DUE = "show_cause_due"    # Part A still On Hold after the first reply — show cause form
    HEARING_DUE = "hearing_due"          # show cause notice issued — hearing record / window form
    REFUSAL_DUE = "refusal_due"          # still On Hold after the post-hearing reply — refusal form
    REFUSED = "refused"
    DESKTOP_APPROVAL_DUE = "desktop_approval_due"    # every item approved — "Approve Desktop Scrutiny" offered
    PHYSICAL = "physical_verification"   # Stage 2 — premises photos per office, then final approval
    APPROVED = "approved"                # final approval given — recorded by the tests, not read by stage()
    OTHER = "other"                      # anything not modelled here


class AdminApplicationReviewPage(BasePage):
    """Officer Console — reviewing a submitted application (/module/admin/dashboard/agency_view.php?id=N,
    the "Review" link in Applications › Desktop scrutiny).

    **Review bars** — each Form-I item (12 for a single key person) has a bar ``.rv[data-key]`` with Approve /
    On Hold radios, a reason list (``.rv-reason``) and a remark (``.rv-rm``, at most 1000 characters). The
    bar's problem or reason text is ``.rv-desc``; the save bar ``#rv-sum`` counts unsaved changes, items not
    reviewed and items that need a reason. "Save review" (``#srv-form``) is refused with a toast while an On
    Hold item has no reason, or "Others" has under 50 characters of remark.

    **Application processing** (``#wfPanel``) — header ``.ui-card-sub`` ("Stage 1 — Desktop Scrutiny · Under
    review"), the four-step track ``.cp-track``, the requested corrections (``#wfCorr``) and the Processing
    history (``.ui-timeline li``, newest first: ``.t-title`` / ``.t-meta`` / ``.t-body``).

    **Decision & next step** (``#wfActions``) offers the next step: ``.rv-btn-flow`` buttons keyed by
    ``data-act`` (``deficiency`` sends Compliance 1, ``accept_reply`` takes the agency's reply into review),
    blocked (``is-blocked``, title "Save your review first") while a review change is unsaved; then the show
    cause form (``#cp…``), the hearing record / window form and finally the refusal form (``#wf…``). Each step
    asks a confirm() and reloads; the client checks are reported in a toast (``#uiToasts .ui-toast``).

    **Approval** (read-only probe on dev, 06-Nov-2026) — once every item is approved and saved, Stage 1 offers
    "Approve Desktop Scrutiny" (``data-act="clear"``; the show cause form stays visible beside it), which moves the
    application to Stage 2 — Physical Verification: review bars ``ph_signboard`` / ``ph_exterior`` /
    ``ph_interior`` per office (``ph_b<n>_…`` for branch offices), "Mark Head office verified"
    (``data-act="0|unit_clear"``, one per office) and "Final approval — issue certificate" (``data-act="clear"``).
    """

    REVIEW_DATA_JS = """() => [...document.querySelectorAll('.rv[data-key]')].map(b => ({
        key: b.dataset.key, orig: b.dataset.orig, state: b.dataset.state,
        choices: [...b.querySelectorAll('input[type=radio]')].map(r => r.value),
        reasons: [...b.querySelectorAll('.rv-reason option')].map(o => o.textContent.trim()),
        remark_placeholder: (b.querySelector('.rv-rm') || {}).placeholder || '',
        remark_max: (b.querySelector('.rv-rm') || {}).maxLength}))"""

    # ── Header ────────────────────────────────────────────────────────────────

    @property
    def main(self):
        return self.page.locator("#adm-main")

    @property
    def read_only_banner(self):
        return self.main.locator(".ui-alert", has_text="Read only.")

    # ── Review bars ───────────────────────────────────────────────────────────

    @property
    def review_bars(self):
        return self.page.locator(".rv[data-key]")

    def review_bar(self, key: str):
        return self.page.locator(f".rv[data-key='{key}']")

    def review_bar_problem(self, key: str):
        """The bar's reason / problem line ("Select a reason", "Others: write at least 50 characters (n/50)")."""
        return self.review_bar(key).locator(".rv-desc")

    @property
    def review_summary(self):
        """The save bar text ("All changes saved · 12 not reviewed", "1 unsaved change(s) · 1 need a reason")."""
        return self.page.locator("#rv-sum")

    @property
    def save_review_button(self):
        return self.page.locator("#srv-form button[type=submit]")

    @property
    def toasts(self):
        return self.page.locator("#uiToasts .ui-toast")

    @property
    def new_toast(self):
        """The first toast shown after the last ``_mark_toasts()``."""
        return self.page.locator("#uiToasts .ui-toast:not([data-seen])").first

    # ── Application processing ────────────────────────────────────────────────

    @property
    def processing_panel(self):
        return self.page.locator("#wfPanel")

    @property
    def stage_subtitle(self):
        """"Stage 1 — Desktop Scrutiny · Under review", "Refused · Closed" …"""
        return self.processing_panel.locator(".ui-card-sub").first

    @property
    def compliance_track(self):
        """The four steps (1. Review, 2. Compliance 1, 3. Compliance 2, 4. Decision); the current one has ``on``."""
        return self.processing_panel.locator(".cp-track > div")

    @property
    def requested_corrections(self):
        return self.page.locator("#wfCorr")

    @property
    def history_items(self):
        """Processing history, newest first."""
        return self.processing_panel.locator(".ui-timeline li")

    @property
    def history_titles(self):
        return self.history_items.locator(".t-title")

    def history_entry(self, title: str):
        """The newest history entry titled ``title`` ("Deficiency", "Agency Reply", "Accept Reply", "Scn Hearing",
        "Grant Window", "Division Report", "Refuse")."""
        return self.history_items.filter(has=self.page.locator(".t-title", has_text=title)).first

    @property
    def decision_block(self):
        return self.page.locator("#wfActions")

    def flow_button(self, act: str):
        """A next-step button by its ``data-act`` (e.g. 'deficiency', 'accept_reply')."""
        return self.page.locator(f".rv-btn-flow[data-act='{act}']").first

    @property
    def flow_buttons(self):
        return self.page.locator(".rv-btn-flow")

    # ── Compliance 2: show cause notice and hearing ───────────────────────────

    @property
    def scn_reason_select(self):
        return self.page.locator("#cpScnReason")

    @property
    def scn_grounds_input(self):
        return self.page.locator("#cpGrounds")

    def hearing_mode_radio(self, mode: str):
        """'personal' or 'virtual'."""
        return self.page.locator(f"input[name='cpMode'][value='{mode}']")

    @property
    def hearing_at_input(self):
        return self.page.locator("#cpAt")

    @property
    def hearing_venue_input(self):
        return self.page.locator("#cpVenue")

    @property
    def issue_scn_button(self):
        return self.page.locator("#cpScnBtn")

    # ── Hearing record and window to correct ──────────────────────────────────

    @property
    def attendance_select(self):
        return self.page.locator("#cpAtt")

    @property
    def window_days_select(self):
        return self.page.locator("#cpDays")

    @property
    def hearing_record_input(self):
        return self.page.locator("#cpRec")

    @property
    def grant_window_button(self):
        return self.page.locator("#cpWinBtn")

    # ── Refusal order ─────────────────────────────────────────────────────────

    @property
    def refusal_reason_select(self):
        return self.page.locator("#wfRejReason")

    @property
    def speaking_order_input(self):
        return self.page.locator("#wfRejAgency")

    @property
    def speaking_order_counter(self):
        return self.page.locator("#wfRejCount")

    @property
    def division_note_input(self):
        return self.page.locator("#wfRejDivision")

    @property
    def refuse_button(self):
        return self.page.locator("#wfRejectBtn")

    # ── Approval ──────────────────────────────────────────────────────────────

    APPROVE_DESKTOP = "Approve Desktop Scrutiny"
    STAGE_2 = "Stage 2 — Physical Verification"

    @property
    def approve_desktop_button(self):
        """Stage 1's approval step (``data-act="clear"``, like Stage 2's final approval), offered once every item
        is approved and saved."""
        return self.page.locator(".rv-btn-flow[data-act='clear']", has_text=self.APPROVE_DESKTOP).first

    @property
    def office_verified_buttons(self):
        """Stage 2: "Mark Head office verified" (``0|unit_clear``) and one per branch office."""
        return self.page.locator("[data-act$='|unit_clear']")

    @property
    def final_approval_button(self):
        """Stage 2: "Final approval — issue certificate"."""
        return self.page.locator("[data-act='clear']").first

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the application review (view id {view_id})")
    def open(self, view_id: int):
        self.navigate(APPLICATION_REVIEW_URL.format(view_id=view_id))
        self.wait_for_load()

    @allure.step("Reload the review page, leaving any unsaved change")
    def reload_discarding_changes(self) -> str:
        """Reloads and accepts the browser's "leave site?" prompt; returns its type ('beforeunload') or ''."""
        seen = []

        def leave(dialog):
            seen.append(dialog.type)
            dialog.accept()

        self.page.on("dialog", leave)
        try:
            self.page.reload()
            self.wait_for_load()
        finally:
            self.page.remove_listener("dialog", leave)
        return seen[0] if seen else ""

    def _mark_toasts(self):
        self.page.evaluate("() => document.querySelectorAll('#uiToasts .ui-toast').forEach(t => t.dataset.seen = '1')")

    def _click_confirm_and_reload(self, button) -> str:
        """Clicks a step button, accepts its confirm() and waits for the reload; returns the prompt text."""
        messages = []
        self.page.once("dialog", lambda d: (messages.append(d.message), d.accept()))
        with self.page.expect_navigation(timeout=20000):
            button.click()
        self.wait_for_load()
        return messages[0] if messages else ""

    def _click_expecting_refusal(self, button) -> str:
        """Clicks a button the page should refuse on the client (no confirm, no reload) and returns the error
        toast. A confirm() means the page let the step through: it is dismissed so nothing is sent, and the
        returned text starts with "CONFIRM: "."""
        self._mark_toasts()
        prompts = []

        def dismiss(dialog):
            prompts.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", dismiss)
        try:
            button.click()
            self.page.wait_for_timeout(300)
        finally:
            self.page.remove_listener("dialog", dismiss)
        if prompts:
            return "CONFIRM: " + prompts[0]
        try:
            self.new_toast.wait_for(timeout=5000)
        except Exception:
            return ""
        return " ".join(self.new_toast.inner_text().split())

    @allure.step("Mark '{key}' {choice} (reason '{reason}') without saving")
    def mark_item(self, key: str, choice: str, reason: str = None, remark: str = None):
        """Sets a review bar's choice ('approved' / 'on_hold'), reason (option value) and remark as the officer
        would. The radios are styled labels, so they are set by script and the page's change / input events
        fired."""
        self.page.evaluate("""([key, choice, reason, remark]) => {
            const bar = document.querySelector(`.rv[data-key="${key}"]`);
            const r = bar.querySelector(`input[type=radio][value="${choice}"]`);
            r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true}));
            if (reason !== null) {
                const s = bar.querySelector('.rv-reason'); s.value = reason;
                s.dispatchEvent(new Event('change', {bubbles: true}));
            }
            if (remark !== null) {
                const m = bar.querySelector('.rv-rm'); m.value = remark;
                m.dispatchEvent(new Event('input', {bubbles: true}));
            }
        }""", [key, choice, reason, remark])

    @allure.step("Click Save review expecting it to be refused")
    def save_review_expecting_refusal(self) -> str:
        """Clicks Save review; returns the error toast (the page stays when the review is incomplete)."""
        return self._click_expecting_refusal(self.save_review_button)

    @allure.step("Review: put '{hold_item}' On Hold ({reason}), approve every other item, save")
    def save_review_with_hold(self, hold_item: str, reason: str, remark: str):
        self.page.evaluate("""([holdKey, reason, remark]) => {
            document.querySelectorAll('.rv[data-key]').forEach(bar => {
                const v = bar.dataset.key === holdKey ? 'on_hold' : 'approved';
                const r = bar.querySelector(`input[type=radio][value="${v}"]`);
                r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true}));
                if (v === 'on_hold') {
                    const s = bar.querySelector('.rv-reason'); s.value = reason;
                    s.dispatchEvent(new Event('change', {bubbles: true}));
                    const m = bar.querySelector('.rv-rm'); m.value = remark;
                    m.dispatchEvent(new Event('input', {bubbles: true}));
                }
            });
        }""", [hold_item, reason, remark])
        with self.page.expect_navigation():
            self.save_review_button.click()
        self.wait_for_load()

    @allure.step("Review: approve every item, save")
    def save_review_all_approved(self):
        self.page.evaluate("""() => document.querySelectorAll('.rv[data-key]').forEach(bar => {
            const r = bar.querySelector('input[type=radio][value="approved"]');
            r.checked = true; r.dispatchEvent(new Event('change', {bubbles: true}));
        })""")
        with self.page.expect_navigation():
            self.save_review_button.click()
        self.wait_for_load()

    @allure.step("Approve Desktop Scrutiny")
    def approve_desktop_scrutiny(self) -> str:
        return self._click_confirm_and_reload(self.approve_desktop_button)

    @allure.step("Mark every office verified")
    def mark_offices_verified(self, limit: int = 10) -> list[str]:
        """Clicks each visible office "verified" button in turn (the page reloads after each); returns the
        confirm texts."""
        prompts = []
        for _ in range(limit):
            visible = [b for b in self.office_verified_buttons.all() if b.is_visible()]
            if not visible:
                break
            prompts.append(self._click_confirm_and_reload(visible[0]))
        return prompts

    @allure.step("Final approval — issue certificate")
    def final_approval(self) -> str:
        return self._click_confirm_and_reload(self.final_approval_button)

    @allure.step("Next step '{act}'")
    def run_flow(self, act: str) -> str:
        return self._click_confirm_and_reload(self.flow_button(act))

    @allure.step("Click next step '{act}' expecting it to be blocked")
    def run_flow_expecting_refusal(self, act: str) -> str:
        return self._click_expecting_refusal(self.flow_button(act))

    @allure.step("Fill the show cause form (reason '{reason}', hearing {minutes_ahead} min ahead)")
    def fill_show_cause(self, reason: str = "", grounds: str = "", venue: str = "", minutes_ahead: int = None):
        """``minutes_ahead`` None leaves the hearing date and time empty."""
        self.scn_reason_select.select_option(reason)
        self.scn_grounds_input.fill(grounds)
        self.hearing_at_input.fill("" if minutes_ahead is None else
                                   (datetime.now(IST) + timedelta(minutes=minutes_ahead)).strftime("%Y-%m-%dT%H:%M"))
        self.hearing_venue_input.fill(venue)

    @allure.step("Click Issue on the show cause form expecting it to be refused")
    def issue_show_cause_expecting_refusal(self) -> str:
        return self._click_expecting_refusal(self.issue_scn_button)

    @allure.step("Issue the show cause notice with a personal hearing")
    def issue_show_cause(self, reason: str, grounds: str, venue: str, minutes_ahead: int = 4) -> str:
        """The hearing is set ``minutes_ahead`` from now (IST); the window can be granted straight away.
        Returns the confirm text."""
        self.fill_show_cause(reason, grounds, venue, minutes_ahead)
        return self._click_confirm_and_reload(self.issue_scn_button)

    @allure.step("Record the hearing and give {days} day(s) to correct again")
    def grant_window(self, attendance: str, days: str, record: str) -> str:
        self.attendance_select.select_option(attendance)
        self.window_days_select.select_option(days)
        self.hearing_record_input.fill(record)
        return self._click_confirm_and_reload(self.grant_window_button)

    @allure.step("Fill the refusal form (reason '{reason}')")
    def fill_refusal(self, reason: str = "", speaking_order: str = "", division_note: str = ""):
        self.refusal_reason_select.select_option(reason)
        self.speaking_order_input.fill(speaking_order)
        self.division_note_input.fill(division_note)

    @allure.step("Click Refuse expecting it to be refused")
    def refuse_expecting_refusal(self) -> str:
        return self._click_expecting_refusal(self.refuse_button)

    @allure.step("Pass the refusal order ({reason})")
    def refuse(self, reason: str, speaking_order: str, division_note: str) -> str:
        self.fill_refusal(reason, speaking_order, division_note)
        return self._click_confirm_and_reload(self.refuse_button)

    # ── Read helpers ──────────────────────────────────────────────────────────

    def main_text(self) -> str:
        return " ".join(self.main.inner_text().split())

    def review_data(self) -> list[dict]:
        """Every review bar: key, orig / state ('pending', 'approved', 'on_hold'), choices, reasons (option
        labels), remark_placeholder, remark_max."""
        return self.page.evaluate(self.REVIEW_DATA_JS)

    def history(self) -> list[str]:
        """History titles, oldest first."""
        return [t.strip() for t in reversed(self.history_titles.all_inner_texts())]

    def select_options(self, select) -> list[str]:
        """Option values of a <select>."""
        return select.locator("option").evaluate_all("os => os.map(o => o.value)")

    def stage(self) -> str:
        """Where the application stands (a ``ReviewStage`` value), read from the controls on the page."""
        visible = lambda loc: loc.count() > 0 and loc.first.is_visible()
        text = self.main_text()
        if "Stage Refused" in text:
            return ReviewStage.REFUSED
        if visible(self.refuse_button):
            return ReviewStage.REFUSAL_DUE
        if visible(self.grant_window_button):
            return ReviewStage.HEARING_DUE
        # Checked before the show cause form: with every item approved after the reply, dev shows both
        if visible(self.approve_desktop_button):
            return ReviewStage.DESKTOP_APPROVAL_DUE
        if visible(self.issue_scn_button):
            return ReviewStage.SHOW_CAUSE_DUE
        if visible(self.flow_button("accept_reply")):
            return ReviewStage.REPLY_RECEIVED
        if visible(self.flow_button("deficiency")):
            return ReviewStage.HELD
        # The subtitle only: Stage 1 pages also say "Reviewed in Stage 2 — Physical Verification" on some items
        if visible(self.stage_subtitle) and self.stage_subtitle.inner_text().strip().startswith(self.STAGE_2):
            return ReviewStage.PHYSICAL
        if "awaiting the agency" in text:
            return ReviewStage.WITH_AGENCY
        bars = self.review_data()
        if self.history() == ["Submitted"] and bars and all(b["orig"] == "pending" for b in bars):
            return ReviewStage.NEW
        if "Stage 1 — Desktop Scrutiny" in text and bars:
            return ReviewStage.IN_REVIEW
        return ReviewStage.OTHER

    def after_hearing(self) -> bool:
        """True once a show cause notice is in the history (the second round of the loop)."""
        return "Scn Hearing" in self.history()
