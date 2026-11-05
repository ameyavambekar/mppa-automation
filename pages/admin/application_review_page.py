from datetime import datetime, timedelta, timezone

import allure

from config import ADMIN_BASE
from pages.base_page import BasePage

APPLICATION_REVIEW_URL = f"{ADMIN_BASE}/dashboard/agency_view.php?id={{view_id}}"
IST = timezone(timedelta(hours=5, minutes=30))


class AdminApplicationReviewPage(BasePage):
    """Officer Console — reviewing a submitted application (/module/admin/dashboard/agency_view.php?id=N,
    the "Review" link in Applications › Desktop scrutiny).

    Each Form-I item has a review bar (``.rv[data-key]``: Approve / On Hold radios, a reason and a remark);
    "Save review" posts them. The "Decision & next step" block then offers the next step as
    ``.rv-btn-flow`` buttons keyed by ``data-act`` (``deficiency`` sends Compliance 1, ``accept_reply`` takes
    the agency's reply into review) or, once a reply has been reviewed with an item still On Hold, the show
    cause form (``#cp…``), the window-to-correct form and finally the refusal form (``#wf…``). Each step asks
    a confirm() and reloads the page.

    Only what driving an application to Refused needs is modelled here (see ``utils.appeal_seeder``).
    """

    # ── Review bars ───────────────────────────────────────────────────────────

    @property
    def review_bars(self):
        return self.page.locator(".rv[data-key]")

    @property
    def save_review_button(self):
        return self.page.locator("#srv-form button[type=submit]")

    @property
    def main(self):
        return self.page.locator("#adm-main")

    def flow_button(self, act: str):
        """A next-step button by its ``data-act`` (e.g. 'deficiency', 'accept_reply')."""
        return self.page.locator(f".rv-btn-flow[data-act='{act}']").first

    # ── Compliance 2: show cause notice and hearing ───────────────────────────

    @property
    def scn_reason_select(self):
        return self.page.locator("#cpScnReason")

    @property
    def scn_grounds_input(self):
        return self.page.locator("#cpGrounds")

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
    def division_note_input(self):
        return self.page.locator("#wfRejDivision")

    @property
    def refuse_button(self):
        return self.page.locator("#wfRejectBtn")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the application review (view id {view_id})")
    def open(self, view_id: int):
        self.navigate(APPLICATION_REVIEW_URL.format(view_id=view_id))
        self.wait_for_load()

    def _click_confirm_and_reload(self, button) -> str:
        """Clicks a step button, accepts its confirm() and waits for the reload; returns the prompt text."""
        messages = []
        self.page.once("dialog", lambda d: (messages.append(d.message), d.accept()))
        with self.page.expect_navigation(timeout=20000):
            button.click()
        self.wait_for_load()
        return messages[0] if messages else ""

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

    @allure.step("Next step '{act}'")
    def run_flow(self, act: str) -> str:
        return self._click_confirm_and_reload(self.flow_button(act))

    @allure.step("Issue the show cause notice with a personal hearing")
    def issue_show_cause(self, reason: str, grounds: str, venue: str, minutes_ahead: int = 4) -> str:
        """The hearing is set ``minutes_ahead`` from now (IST); the window can be granted straight away."""
        self.scn_reason_select.select_option(reason)
        self.scn_grounds_input.fill(grounds)
        self.hearing_at_input.fill((datetime.now(IST) + timedelta(minutes=minutes_ahead)).strftime("%Y-%m-%dT%H:%M"))
        self.hearing_venue_input.fill(venue)
        return self._click_confirm_and_reload(self.issue_scn_button)

    @allure.step("Record the hearing and give {days} day(s) to correct again")
    def grant_window(self, attendance: str, days: str, record: str) -> str:
        self.attendance_select.select_option(attendance)
        self.window_days_select.select_option(days)
        self.hearing_record_input.fill(record)
        return self._click_confirm_and_reload(self.grant_window_button)

    @allure.step("Pass the refusal order ({reason})")
    def refuse(self, reason: str, speaking_order: str, division_note: str) -> str:
        self.refusal_reason_select.select_option(reason)
        self.speaking_order_input.fill(speaking_order)
        self.division_note_input.fill(division_note)
        return self._click_confirm_and_reload(self.refuse_button)

    # ── Read helpers ──────────────────────────────────────────────────────────

    def main_text(self) -> str:
        return " ".join(self.main.inner_text().split())
