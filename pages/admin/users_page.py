import re

import allure

from config import ADMIN_BASE
from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage

OFFICERS_URL = f"{ADMIN_BASE}/users/index.php"

_API_JS = """async ([route, data, query]) => {
  try { return {ok: true, data: await Portal.api(route, data, {silent: true, query: query || {}})}; }
  catch (e) { return {ok: false, msg: e.message, code: e.code || null}; }
}"""


class OfficersPage(BasePage):
    """Officers & Access (Administration › Officers & access, /module/admin/users/index.php).

    A JS page over the portal API: the list (``#rows``) is loaded with ``admins.list?q=`` and redrawn after
    every save / toggle / delete without a page reload. Add / Edit open the ``#frm`` dialog (form
    ``#frmBody``); each field sits in a ``.ui-field[data-f=<name>]`` box whose ``.f-err`` holds its message.
    Results appear as toasts (``#uiToasts .ui-toast``); Deactivate and Delete ask with a browser confirm().

    Rows are keyed by username (the muted line under the officer's name is "<username>" or
    "<username> · <designation>").
    """

    ROLE_VALUES = {"Commissioner (State)": "commissioner", "Divisional Officer": "division",
                   "District Officer": "district", "Super Administrator": "superadmin"}

    # ── Page ──────────────────────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        return AdminSidebar(self.page)

    @property
    def heading(self):
        return self.page.locator("main h2")

    @property
    def sub_heading(self):
        return self.page.locator("main h2 + p")

    @property
    def search_input(self):
        return self.page.locator("#q")

    @property
    def add_button(self):
        return self.page.get_by_role("button", name="Add officer", exact=True)

    @property
    def table(self):
        return self.page.locator("main table")

    @property
    def table_headers(self):
        return self.table.locator("thead th")

    @property
    def rows(self):
        return self.page.locator("#rows tr")

    @property
    def officer_rows(self):
        """Rows that hold an officer (not the 'No officers found.' row)."""
        return self.page.locator("#rows tr:has(td:nth-child(7))")

    @property
    def empty_row(self):
        return self.page.locator("#rows td", has_text="No officers found.")

    @property
    def toast(self):
        return self.page.locator("#uiToasts .ui-toast").last

    @property
    def access_denied(self):
        return self.page.get_by_text(re.compile(r"Access denied"))

    def row(self, username: str):
        return self.rows.filter(has=self.page.locator(
            "td:first-child div.ui-muted", has_text=re.compile(rf"^{re.escape(username)}( ·|$)")))

    def rows_with_role(self, label: str):
        return self.rows.filter(has=self.page.locator("td:nth-child(2) .ui-badge", has_text=re.compile(rf"^{re.escape(label)}$")))

    def cell(self, username: str, index: int):
        """0 Officer · 1 Role · 2 Area · 3 Contact · 4 Last login · 5 Status · 6 actions."""
        return self.row(username).locator("td").nth(index)

    def officer_sub_line(self, username: str):
        return self.cell(username, 0).locator("div.ui-muted")

    def role_badge(self, username: str):
        return self.cell(username, 1).locator(".ui-badge")

    def status_badge(self, username: str):
        return self.cell(username, 5).locator(".ui-badge")

    def action_buttons(self, row):
        return row.locator("td:nth-child(7) button")

    def edit_button(self, username: str):
        return self.row(username).get_by_role("button", name="Edit")

    def deactivate_button(self, username: str):
        return self.row(username).get_by_role("button", name="Deactivate")

    def activate_button(self, username: str):
        return self.row(username).get_by_role("button", name="Activate")

    def delete_button(self, username: str):
        return self.row(username).get_by_role("button", name="Delete")

    # ── Add / Edit officer dialog ────────────────────────────────────────────

    @property
    def dialog(self):
        return self.page.locator("#frm")

    @property
    def dialog_title(self):
        return self.page.locator("#frmTitle")

    @property
    def close_button(self):
        return self.dialog.locator(".ui-card-head").get_by_role("button", name="Close")

    @property
    def cancel_button(self):
        return self.dialog.get_by_role("button", name="Cancel")

    @property
    def save_button(self):
        return self.page.locator("#saveBtn")

    @property
    def form_error(self):
        return self.page.locator("#formErr")

    @property
    def role_select(self):
        return self.page.locator("#f_role")

    @property
    def division_select(self):
        return self.page.locator("#f_div")

    @property
    def district_select(self):
        return self.page.locator("#f_dist")

    @property
    def division_field(self):
        return self.page.locator("#w_div")

    @property
    def district_field(self):
        return self.page.locator("#w_dist")

    @property
    def full_name_input(self):
        return self.page.locator("#f_name")

    @property
    def designation_input(self):
        return self.page.locator("#f_desig")

    @property
    def username_input(self):
        return self.page.locator("#f_user")

    @property
    def email_input(self):
        return self.page.locator("#f_email")

    @property
    def mobile_input(self):
        return self.page.locator("#f_mob")

    @property
    def password_input(self):
        return self.page.locator("#f_pass")

    @property
    def confirm_input(self):
        return self.page.locator("#f_pass2")

    @property
    def password_show_button(self):
        return self.page.locator('[data-f="password"] .pw-toggle')

    @property
    def password_rules(self):
        return self.page.locator("#pwRules li")

    @property
    def password_rules_met(self):
        return self.page.locator("#pwRules li.ok")

    @property
    def password_bar(self):
        return self.page.locator("#pwBar")

    @property
    def password_required_mark(self):
        return self.page.locator("#passReq")

    @property
    def password_help(self):
        return self.page.locator("#passHelp")

    def field_box(self, name: str):
        """name: role, division_id, district_id, full_name, designation, username, email, mobile, password, confirm."""
        return self.page.locator(f'#frmBody [data-f="{name}"]')

    def field_error(self, name: str):
        return self.field_box(name).locator(".f-err")

    def field_help(self, name: str):
        return self.field_box(name).locator(".ui-help")

    # ── Actions ───────────────────────────────────────────────────────────────

    def _list_reload(self):
        return self.page.expect_response(lambda r: "r=admins.list" in r.url)

    @allure.step("Open Officers & Access")
    def open(self):
        with self._list_reload():
            self.navigate(OFFICERS_URL)
        self.wait_for_load()

    @allure.step("Search officers for '{text}'")
    def search(self, text: str):
        with self._list_reload():
            self.search_input.fill(text)

    @allure.step("Click 'Add officer'")
    def open_add_form(self):
        self.add_button.click()
        self.dialog_title.wait_for()

    @allure.step("Click Edit on '{username}'")
    def open_edit_form(self, username: str):
        self.edit_button(username).click()
        self.page.wait_for_function("document.getElementById('frm').classList.contains('is-open')")

    @allure.step("Choose role '{label}'")
    def choose_role(self, label: str):
        self.role_select.select_option(label=label)

    @allure.step("Choose division '{label}'")
    def choose_division(self, label: str):
        with self.page.expect_response(lambda r: "r=meta.districts" in r.url):
            self.division_select.select_option(label=label)
        self.page.wait_for_function("document.querySelectorAll('#f_dist option').length > 1")

    @allure.step("Choose district '{label}'")
    def choose_district(self, label: str):
        self.district_select.select_option(label=label)

    def type_into(self, locator, text: str):
        """Fills a field (input event → live check) and leaves it (blur → tidy + check)."""
        locator.fill(text)
        locator.blur()

    @allure.step("Fill the officer form")
    def fill_form(self, data, password: bool = True):
        self.choose_role(data.role_label)
        if data.division:
            self.choose_division(data.division)
        if data.district:
            self.choose_district(data.district)
        self.fill_details(data, password)

    @allure.step("Fill name, designation, username, email, mobile (and password)")
    def fill_details(self, data, password: bool = True):
        self.type_into(self.full_name_input, data.full_name)
        self.type_into(self.designation_input, data.designation)
        self.type_into(self.username_input, data.username)
        self.type_into(self.email_input, data.email)
        self.type_into(self.mobile_input, data.mobile)
        if password:
            self.type_into(self.password_input, data.password)
            self.type_into(self.confirm_input, data.password)

    @allure.step("Click Save")
    def save(self, expect_saved: bool = True):
        """Clicks Save. With expect_saved, waits for the list to reload after the save."""
        if not expect_saved:
            self.save_button.click()
            return
        with self._list_reload():
            self.save_button.click()

    @allure.step("Click Deactivate on '{username}' (prompt: {action})")
    def deactivate(self, username: str, action: str = "accept") -> str:
        if action != "accept":
            return self.click_and_handle_alert(self.deactivate_button(username), action=action)
        with self._list_reload():
            return self.click_and_handle_alert(self.deactivate_button(username), action=action)

    @allure.step("Click Activate on '{username}'")
    def activate(self, username: str) -> str:
        """Returns the text of any prompt shown ('' when none — Activate has no prompt)."""
        with self._list_reload():
            return self.click_and_handle_alert(self.activate_button(username), action="accept")

    @allure.step("Click Delete on '{username}' (prompt: {action})")
    def delete(self, username: str, action: str = "accept") -> str:
        if action != "accept":
            return self.click_and_handle_alert(self.delete_button(username), action=action)
        with self._list_reload():
            return self.click_and_handle_alert(self.delete_button(username), action=action)

    # ── Reading / API (no assertions) ────────────────────────────────────────

    def api(self, route: str, data=None, query=None) -> dict:
        """Calls the portal API in this browser session: {'ok': True, 'data': …} or {'ok': False, 'msg': …}."""
        return self.page.evaluate(_API_JS, [route, data, query])

    def list_officers(self, q: str = "") -> list[dict]:
        res = self.api("admins.list", None, {"q": q})
        return res.get("data") or []

    def find_officer(self, username: str):
        return next((r for r in self.list_officers(username) if r["username"] == username), None)

    def division_id(self, name: str) -> str:
        return self.division_select.locator("option", has_text=re.compile(rf"^{re.escape(name)}$")).get_attribute("value")

    def district_id(self, division: str, district: str) -> str:
        res = self.api("meta.districts", None, {"division_id": self.division_id(division)})
        return str(next(d["id"] for d in res["data"] if d["district_name"] == district))

    def save_payload(self, data) -> dict:
        """The JSON the form sends to admins.save for ``data`` (no id → create)."""
        return {"id": "", "role": data.role, "full_name": data.full_name, "designation": data.designation,
                "username": data.username, "email": data.email, "mobile": data.mobile, "password": data.password,
                "division_id": self.division_id(data.division) if data.division else "",
                "district_id": self.district_id(data.division, data.district) if data.district else ""}

    def row_texts(self) -> list[str]:
        return self.officer_rows.evaluate_all("rs => rs.map(r => r.innerText.replace(/\\s+/g, ' ').trim())")

    def dispatch_paste(self, locator) -> bool:
        """Fires a paste event on the field; True when the page blocked it."""
        return locator.evaluate("""el => { const e = new ClipboardEvent('paste', {clipboardData: new DataTransfer(),
            bubbles: true, cancelable: true}); el.dispatchEvent(e); return e.defaultPrevented; }""")
