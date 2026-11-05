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

    Used to answer compliance notices while preparing appeal test data (``utils.appeal_seeder``); the
    answers keep the submitted values and add a note. Document items are not handled.
    """

    @allure.step("Open Corrections")
    def open(self):
        self.navigate(CORRECTIONS_URL)
        self.wait_for_load()

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
