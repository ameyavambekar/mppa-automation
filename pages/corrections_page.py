import allure

from config import FORMS_BASE
from pages.base_page import BasePage

CORRECTIONS_URL = f"{FORMS_BASE}/corrections.php"

# The page's own client (``Portal.api``) — the same calls its Save and Send buttons make.
_API_JS = """async ([route, data, query]) => {
  try { return {ok: true, data: await Portal.api(route, data, {silent: true, query: query || {}})}; }
  catch (e) { return {ok: false, msg: e.message}; }
}"""


class AgencyCorrectionsPage(BasePage):
    """Agency — Corrections (/module/agency/forms/corrections.php): the items an officer put On Hold, each
    re-opened for editing, and "Send reply" once they are answered.

    The page draws its list from ``corrections.list``: ``#crSub`` (how many items are left and the reply
    date), one ``.cr-item`` per item (label, badge, "Officer's remarks:" and a "Correct details" button that
    opens the section's fields with a note box — required when nothing is changed — and "Save corrections";
    a saved item is locked), and the reply form ``#replyForm`` in ``#crReply``, shown once every item is
    corrected (at least 10 characters).

    ``answer_open_items`` / ``send_reply`` make the same calls through ``Portal.api`` and are used to answer
    compliance notices while preparing appeal test data (``utils.appeal_seeder``); the answers keep the
    submitted values and add a note. Document items are not handled.
    """

    # ── Page ──────────────────────────────────────────────────────────────────

    @property
    def subtitle(self):
        """"1 item(s) still to correct · Reply by YYYY-MM-DD", "All items corrected — send your reply below",
        "Your corrections and reply have been submitted — the officer is reviewing them." …"""
        return self.page.locator("#crSub")

    @property
    def items(self):
        return self.page.locator(".cr-item")

    def item(self, label: str):
        """A correction item by its label (e.g. "Part A — Agency details")."""
        return self.items.filter(has=self.page.locator(".cr-head strong", has_text=label)).first

    def item_badge(self, label: str):
        """"Correction needed", "Corrected", "Accepted by officer", "Not corrected"."""
        return self.item(label).locator(".cr-head .ui-badge")

    def item_remarks(self, label: str):
        return self.item(label).locator(".cr-reason")

    def item_locked_note(self, label: str):
        return self.item(label).locator(".ui-alert-success")

    def correct_details_button(self, label: str):
        return self.item(label).locator("[data-open]")

    def section_form(self, label: str):
        return self.item(label).locator(".cr-sec form")

    def section_field(self, label: str, name: str):
        return self.section_form(label).locator(f"[name='{name}']")

    def section_note(self, label: str):
        return self.section_form(label).locator("textarea[name='__note']")

    def section_error(self, label: str):
        return self.section_form(label).locator(".cr-formerr")

    @property
    def reply_section(self):
        return self.page.locator("#crReply")

    @property
    def reply_text(self):
        return self.page.locator("#replyForm [name='text']")

    @property
    def reply_button(self):
        return self.page.locator("#replyForm button[type=submit], #replyForm button").first

    @property
    def new_toast(self):
        return self.page.locator("#uiToasts .ui-toast:not([data-seen])").first

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open Corrections")
    def open(self):
        self.navigate(CORRECTIONS_URL)
        self.wait_for_load()
        self.page.wait_for_function("() => document.getElementById('crSub').textContent.trim() !== ''")

    def _mark_toasts(self):
        self.page.evaluate("() => document.querySelectorAll('#uiToasts .ui-toast').forEach(t => t.dataset.seen = '1')")

    @allure.step("Open '{label}' for correction")
    def open_section(self, label: str):
        self.correct_details_button(label).click()
        self.section_form(label).wait_for()

    @allure.step("Fill required fields the section left blank")
    def fill_blank_fields(self, label: str, values: dict):
        """Fills each field in ``values`` ({name: value}) that is empty in the open section."""
        for name, value in values.items():
            field = self.section_field(label, name)
            if value and field.count() and not field.input_value().strip():
                field.fill(value)

    @allure.step("Save the corrections of '{label}' (note: '{note}')")
    def save_section(self, label: str, note: str) -> str:
        """Writes ``note`` and clicks Save corrections, accepting the confirm. Returns the confirm text ("" when
        the page refused on the client). Waits until the item is re-drawn or the form shows an error."""
        self.section_note(label).fill(note)
        prompts = []

        def accept(dialog):
            prompts.append(dialog.message)
            dialog.accept()

        self.page.on("dialog", accept)
        try:
            self.section_form(label).locator("button[type=submit]").click()
            self._wait_for_section_result(label)
        finally:
            self.page.remove_listener("dialog", accept)
        return prompts[0] if prompts else ""

    def _wait_for_section_result(self, label: str):
        """Waits until the item is re-drawn (saved), or the form shows a server error or a field error."""
        self.page.wait_for_function("""label => {
            const it = [...document.querySelectorAll('.cr-item')].find(i => i.querySelector('.cr-head strong')
                         .textContent.includes(label));
            if (!it) return false;
            const err = it.querySelector('.cr-formerr');
            const fieldErr = [...it.querySelectorAll('.cr-err')].some(e => e.textContent.trim());
            return !it.querySelector('.cr-sec form') || fieldErr
                   || (err && err.style.display !== 'none' && err.textContent.trim());
        }""", arg=label, timeout=20000)

    @allure.step("Send the reply '{text}' from the reply form")
    def submit_reply(self, text: str) -> tuple[str, str]:
        """Writes ``text`` and clicks Submit corrections, accepting the confirm. Returns (confirm text, message):
        the toast, or — when the browser itself blocks the submit (the box has ``minlength="10" required``) —
        its validation message."""
        self._mark_toasts()
        prompts = []

        def accept(dialog):
            prompts.append(dialog.message)
            dialog.accept()

        self.page.on("dialog", accept)
        try:
            self.reply_text.fill(text)
            native = self.reply_text.evaluate("t => t.validity.valid ? '' : t.validationMessage")
            self.reply_button.click()
            if native:
                return "", native
            try:
                self.new_toast.wait_for(timeout=10000)
                toast = " ".join(self.new_toast.inner_text().split())
            except Exception:
                toast = ""
        finally:
            self.page.remove_listener("dialog", accept)
        return (prompts[0] if prompts else ""), toast

    def _api(self, route: str, data: dict = None, query: dict = None) -> dict:
        return self.page.evaluate(_API_JS, [route, data, query])

    def open_items(self) -> list[dict]:
        """Correction items still open (``id``, ``item_type``, ``status`` …)."""
        listed = self._api("corrections.list")
        return [c for c in (listed.get("data") or {}).get("items", []) if c.get("status") == "open"]

    @allure.step("Answer every open correction without changing the details")
    def answer_open_items(self, note: str, blanks: dict = None) -> list[str]:
        """Saves each open section as it stands, filling any required field the portal left blank from
        ``blanks`` (e.g. {'email': …, 'mobile': …}). Returns the problems met (empty when all were saved)."""
        problems = []
        for item in self.open_items():
            if item.get("item_type") == "document":
                problems.append(f"correction {item['id']} is a document — not handled")
                continue
            section = self._api("corrections.section", None, {"correction_id": item["id"]})
            if not section.get("ok"):
                problems.append(f"correction {item['id']}: {section.get('msg')}")
                continue
            fields = {f["name"]: f["value"] for f in section["data"]["fields"]}
            for name, value in (blanks or {}).items():
                if name in fields and not fields[name] and value:
                    fields[name] = value
            saved = self._api("corrections.save_section", {"correction_id": item["id"], "fields": fields, "note": note})
            if not saved.get("ok"):
                problems.append(f"correction {item['id']}: {saved.get('msg')}")
        return problems

    @allure.step("Send the reply to the officer")
    def send_reply(self, text: str) -> dict:
        return self._api("applications.reply", {"text": text})
