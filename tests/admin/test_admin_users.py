"""
Officers & Access — Admin Portal (KAN-34)
=========================================
Covers KAN-TC-268…279 and 725…740 for Officers & Access (Administration ›
Officers & access, /module/admin/users/index.php), rewritten 04-Nov-2026 for
the redesigned page. The old "Admin User Management" page (Legacy admin tools,
/module/admin/admins/index.php) is out of scope.

Test data: every officer a test changes, logs in as or deletes is a NEW test
officer it creates itself (``new_officers``: run-unique ``qatest…`` username,
random password generated per run) and is deleted on teardown. No test edits,
deactivates or deletes an officer that already exists on the portal; tests that
read existing rows (TC-268, 269, 730, 736) only read them.

Known failures on dev (04-Nov-2026), page behaviour — MPPA sheet, "Super admin" tab:
  TC-273, TC-276  #85, #86 a deactivated / deleted officer's open session keeps working (their next page loads)
  TC-734          #87 the server saves a 4-character username, a username starting with a digit, digits in the
                      name, the password "password" and a password containing the username
  TC-736          #88 searching for % or _ lists every officer
"""

import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import allure
from playwright.sync_api import expect

from pages.admin.audit_log_page import AdminAuditLogPage
from pages.admin.components.sidebar import AdminSidebar
from pages.admin.dashboard_page import ADMIN_DASHBOARD_URL
from pages.admin.users_page import OFFICERS_URL, OfficersPage
from test_data.admin_users_factory import OfficerData, OfficersFactory
from utils.aio import aio_case

STORY = "Officers & Access"
F = OfficersFactory
OPEN = re.compile(r"\bis-open\b")
LOGIN_URL = re.compile(r"/admin/auth/login\.php")


def _now_ist() -> datetime:
    return datetime.now(timezone(timedelta(hours=5, minutes=30))).replace(tzinfo=None)


def _audit_entries(page, action: str, text: str):
    """Today's Audit log entries with the action pill ``action`` whose text contains ``text`` (e.g. 'ID #52')."""
    audit = AdminAuditLogPage(page)
    audit.open(date_f="today")
    return audit.log_entries.filter(has=page.locator(".act-pill", has_text=re.compile(rf"^\s*{re.escape(action)}\s*$"))) \
        .filter(has_text=text)


def _buttons(row) -> list[str]:
    return [b.strip() for b in row.locator("td:nth-child(7) button").all_inner_texts()]


def _rows_summary(op: OfficersPage) -> list[dict]:
    return op.officer_rows.evaluate_all("""rs => rs.map(r => ({role: r.cells[1].innerText.trim(),
        buttons: [...r.cells[6].querySelectorAll('button')].map(b => b.innerText.trim())}))""")


# ---------------------------------------------------------------------------
# TC-268  List
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-268")
@allure.story(STORY)
@allure.title("TC-268: Officers & Access lists every officer with name, role, area, contact, last login and status")
def test_tc268_officer_list(logged_in_officers_page: OfficersPage):
    """
    Given I am on the Officer Console dashboard as the Super Administrator
    When  I click Administration › Officers & access
    Then  the page opens with its heading, search, Add officer and the columns Officer, Role, Area, Contact,
          Last login, Status; the Super Administrator is first and roles follow Commissioner, Divisional, District
    And   District / Divisional rows show the expected name, area, contact, last login, status and actions

    AIO: KAN-TC-268 | KAN-34 AC-1 | data: existing officers (read only)
    """
    op = logged_in_officers_page

    with allure.step("Click 'Officers & access' in the sidebar of the dashboard"):
        op.page.goto(ADMIN_DASHBOARD_URL)
        op.sidebar.go_to_officers()
        expect(op.page).to_have_url(OFFICERS_URL)
        expect(op.sidebar.active_item).to_contain_text(F.SIDEBAR_LINK)
        expect(op.page).to_have_title(F.TITLE)

    with allure.step("Verify the top of the page"):
        expect(op.heading).to_have_text(F.HEADING)
        expect(op.sub_heading).to_have_text(F.SUB_HEADING)
        expect(op.search_input).to_have_attribute("placeholder", F.SEARCH_PLACEHOLDER)
        expect(op.add_button).to_be_visible()

    with allure.step("Verify the columns and the order of the list"):
        assert op.table_headers.evaluate_all("hs => hs.map(h => h.textContent.trim())") == F.COLUMNS
        officers = op.list_officers()
        expect(op.officer_rows).to_have_count(len(officers))
        ranks = [F.ROLE_ORDER.index(o["role"]) for o in officers]
        assert ranks == sorted(ranks), "Roles are not ordered Super Administrator, Commissioner, Divisional, District"
        expect(op.officer_rows.first.locator(".ui-badge").first).to_have_text(F.ROLE_LABELS["superadmin"])

    for role in ("district", "division"):
        o = next(x for x in officers if x["role"] == role)
        with allure.step(f"Verify the {F.ROLE_LABELS[role]} row '{o['username']}'"):
            u = o["username"]
            expect(op.cell(u, 0).locator("strong")).to_have_text(o["full_name"])
            expect(op.officer_sub_line(u)).to_have_text(u + (f" · {o['designation']}" if o["designation"] else ""))
            expect(op.role_badge(u)).to_have_text(F.ROLE_LABELS[role])
            area = f"{o['district_name']} ({o['division_name']})" if role == "district" else f"{o['division_name']} Division"
            expect(op.cell(u, 2)).to_have_text(area)
            expect(op.cell(u, 3)).to_contain_text(o["email"])
            expect(op.cell(u, 4)).to_have_text(re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|Never)$"))
            expect(op.status_badge(u)).to_have_text(re.compile(r"^(Active|Inactive)$"))
            assert _buttons(op.row(u).first) in (["Edit", "Deactivate", "Delete"], ["Edit", "Activate", "Delete"])


# ---------------------------------------------------------------------------
# TC-269  Super Administrator rows
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-269")
@allure.story(STORY)
@allure.title("TC-269: Super Administrator rows have no action buttons")
def test_tc269_super_admin_rows_protected(logged_in_officers_page: OfficersPage):
    """
    Given I am on Officers & Access as the Super Administrator
    Then  every Super Administrator row has no Edit, Deactivate or Delete button
    And   every other row has Edit, Deactivate (or Activate) and Delete

    AIO: KAN-TC-269 | KAN-34 AC-3 | data: existing officers (read only)
    """
    rows = _rows_summary(logged_in_officers_page)

    with allure.step("Verify the Super Administrator rows"):
        supers = [r for r in rows if r["role"] == F.ROLE_LABELS["superadmin"]]
        assert supers and all(r["buttons"] == [] for r in supers), supers

    with allure.step("Verify the other rows"):
        bad = [r for r in rows if r["role"] != F.ROLE_LABELS["superadmin"]
               and r["buttons"] not in (["Edit", "Deactivate", "Delete"], ["Edit", "Activate", "Delete"])]
        assert not bad, bad[:5]


# ---------------------------------------------------------------------------
# TC-270  Add officer
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-270")
@allure.story(STORY)
@allure.title("TC-270: Add officer creates a District Officer listed as Active with Last login Never")
def test_tc270_add_officer(logged_in_officers_page: OfficersPage, new_officers, district_officer_data: OfficerData):
    """
    Given I am on Officers & Access as the Super Administrator
    When  I add a District Officer (Pune / Pune) with valid details
    Then  "District Officer account '<username>' created." is shown and the officer is listed as Active,
          Last login "Never", and the Audit log records Admin Created

    AIO: KAN-TC-270 | KAN-34 AC-4 | data: {district_officer_data.scenario_label}
    """
    op, data = logged_in_officers_page, district_officer_data

    with allure.step("Click 'Add officer'"):
        op.open_add_form()
        expect(op.dialog_title).to_have_text(F.ADD_TITLE)
        expect(op.role_select.locator("option:checked")).to_have_text(F.DEFAULT_ROLE)
        expect(op.division_field).to_be_hidden()
        expect(op.district_field).to_be_hidden()

    with allure.step("Choose District Officer, Division Pune, District Pune"):
        op.choose_role(data.role_label)
        expect(op.division_field).to_be_visible()
        expect(op.district_select.locator("option")).to_have_text([F.DISTRICT_PLACEHOLDER])
        op.choose_division(data.division)
        expect(op.district_select.locator("option")).to_have_text(F.PUNE_DISTRICTS)
        op.choose_district(data.district)

    with allure.step("Enter the officer's details and password"):
        op.fill_details(data)
        for name in ("full_name", "designation", "username", "email", "mobile", "password"):
            expect(op.field_box(name)).to_have_class(re.compile(r"\bis-valid\b"))
        expect(op.password_rules_met).to_have_count(len(F.PASSWORD_RULES))

    with allure.step("Click Save"):
        op.save()
        expect(op.toast).to_have_text(F.created_toast(data))
        new_officers.track(data)
        expect(op.dialog).not_to_have_class(OPEN)

    with allure.step("Verify the new officer's row"):
        u = data.username
        expect(op.officer_sub_line(u)).to_have_text(f"{u} · {data.designation}")
        expect(op.role_badge(u)).to_have_text(data.role_label)
        expect(op.cell(u, 2)).to_have_text(f"{data.district} ({data.division})")
        expect(op.cell(u, 3)).to_contain_text(data.email)
        expect(op.cell(u, 3)).to_contain_text(data.mobile)
        expect(op.cell(u, 4)).to_have_text(F.NEVER)
        expect(op.status_badge(u)).to_have_text("Active")

    with allure.step("Verify the Audit log records Admin Created"):
        entry = _audit_entries(op.page, F.AUDIT_CREATED, f"ID #{data.id}")
        expect(entry).to_have_count(1)
        expect(entry).to_contain_text("super")
        expect(entry).to_contain_text(data.role)


# ---------------------------------------------------------------------------
# TC-271 / TC-272  Duplicates
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-271")
@allure.story(STORY)
@allure.title("TC-271: A username already in use is refused, in any letter case")
def test_tc271_duplicate_username(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given a new test officer A exists
    When  I type A's username (and then in capitals) in Add officer and Save
    Then  "This username is already in use." and "Please correct the highlighted fields." are shown and nothing
          is saved; a save sent straight to the server is refused with "Another account already uses this
          username or email."

    AIO: KAN-TC-271 | KAN-34 AC-7 | data: new_district_officer
    """
    op = logged_in_officers_page
    a = new_officers.create(officers_data.district_officer())
    op.open()
    other = replace(officers_data.district_officer(), username=a.username.upper())

    with allure.step("Type A's username, then in capitals"):
        op.open_add_form()
        op.type_into(op.username_input, a.username)
        expect(op.field_error("username")).to_have_text(F.MSG["user_taken"])
        op.type_into(op.username_input, a.username.upper())
        expect(op.field_error("username")).to_have_text(F.MSG["user_taken"])

    with allure.step("Fill the other fields with new values and click Save"):
        op.fill_form(other)
        op.save(expect_saved=False)
        expect(op.form_error).to_have_text(F.FORM_ERROR)
        expect(op.dialog).to_have_class(OPEN)

    with allure.step("Send the same save straight to the server"):
        res = op.api("admins.save", op.save_payload(other))
        if res["ok"]:
            new_officers.track_id(res["data"]["id"], other.username)
        assert not res["ok"] and res["msg"] == F.SERVER_DUPLICATE, res

    with allure.step("Verify only one officer has that username"):
        assert [o["username"].lower() for o in op.list_officers(a.username)].count(a.username.lower()) == 1


@aio_case("KAN-TC-272")
@allure.story(STORY)
@allure.title("TC-272: An email already in use is refused, in any letter case")
def test_tc272_duplicate_email(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given a new test officer A exists
    When  I type A's email (and then in capitals) in Add officer and Save
    Then  "This email is already used by another officer." is shown and nothing is saved; the server refuses
          the same save with "Another account already uses this username or email."

    AIO: KAN-TC-272 | KAN-34 AC-7 | data: new_district_officer
    """
    op = logged_in_officers_page
    a = new_officers.create(officers_data.district_officer())
    op.open()
    other = replace(officers_data.district_officer(), email=a.email.upper())

    with allure.step("Type A's email, then in capitals"):
        op.open_add_form()
        op.type_into(op.email_input, a.email)
        expect(op.field_error("email")).to_have_text(F.MSG["email_taken"])
        op.type_into(op.email_input, a.email.upper())
        expect(op.field_error("email")).to_have_text(F.MSG["email_taken"])

    with allure.step("Fill the other fields with new values and click Save"):
        op.fill_form(other)
        op.save(expect_saved=False)
        expect(op.form_error).to_have_text(F.FORM_ERROR)

    with allure.step("Send the same save straight to the server"):
        res = op.api("admins.save", op.save_payload(other))
        if res["ok"]:
            new_officers.track_id(res["data"]["id"], other.username)
        assert not res["ok"] and res["msg"] == F.SERVER_DUPLICATE, res

    with allure.step("Verify nobody else has that email"):
        assert [o["email"].lower() for o in op.list_officers(a.email)].count(a.email.lower()) == 1


# ---------------------------------------------------------------------------
# TC-273  Deactivate
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-273")
@allure.story(STORY)
@allure.title("TC-273: Deactivate blocks the officer's login, ends their open session and records ADMIN_DEACTIVATE")
def test_tc273_deactivate(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given a new test officer is logged in in another browser
    When  I click Deactivate and Cancel, then Deactivate and OK
    Then  Cancel changes nothing; OK shows "Account deactivated.", Inactive and an Activate button; the officer
          cannot log in ("Invalid username or password."); the Audit log records ADMIN_DEACTIVATE and
          ADMIN_LOGIN_FAILED; the officer's open session is ended

    AIO: KAN-TC-273 | KAN-34 AC-8, EC-2, EC-3 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()

    with allure.step("Log the test officer in in another browser"):
        officer_page, error = officer_login(o)
        assert not error, error

    with allure.step("Click Deactivate and Cancel"):
        assert op.deactivate(o.username, action="dismiss") == F.CONFIRM_DEACTIVATE
        expect(op.status_badge(o.username)).to_have_text("Active")

    with allure.step("Click Deactivate and OK"):
        assert op.deactivate(o.username) == F.CONFIRM_DEACTIVATE
        expect(op.toast).to_have_text(F.DEACTIVATED)
        expect(op.status_badge(o.username)).to_have_text("Inactive")
        expect(op.activate_button(o.username)).to_have_class(re.compile("ui-btn-success"))
        expect(op.deactivate_button(o.username)).to_have_count(0)

    with allure.step("Try to log in as the deactivated officer"):
        _, error = officer_login(o)
        assert error == F.LOGIN_REFUSED, error

    with allure.step("Verify the Audit log"):
        expect(_audit_entries(op.page, F.AUDIT_DEACTIVATED, f"ID #{o.id}")).to_have_count(1)
        expect(_audit_entries(op.page, F.AUDIT_LOGIN_FAILED, o.username).first).to_be_visible()

    with allure.step("Reload the officer's open page in the other browser"):
        officer_page.reload()
        expect(officer_page).to_have_url(LOGIN_URL)


# ---------------------------------------------------------------------------
# TC-274  Activate
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-274")
@allure.story(STORY)
@allure.title("TC-274: Activate restores the officer's login and records ADMIN_ACTIVATE")
def test_tc274_activate(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given a new test officer is Inactive
    When  I click Activate
    Then  no prompt is shown, "Account activated." is shown, the officer is Active with a Deactivate button,
          can log in with their password, Last login shows that login and the Audit log records ADMIN_ACTIVATE

    AIO: KAN-TC-274 | KAN-34 AC-9 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    assert op.api("admins.toggle", {"id": o.id, "active": 0})["ok"]
    op.open()
    expect(op.status_badge(o.username)).to_have_text("Inactive")

    with allure.step("Click Activate"):
        assert op.activate(o.username) == ""
        expect(op.toast).to_have_text(F.ACTIVATED)
        expect(op.status_badge(o.username)).to_have_text("Active")
        expect(op.deactivate_button(o.username)).to_be_visible()

    with allure.step("Log in as the officer in another browser"):
        officer_page, error = officer_login(o)
        assert not error, error
        expect(officer_page).not_to_have_url(LOGIN_URL)
        logged_in_at = _now_ist()

    with allure.step("Verify Last login"):
        op.open()
        shown = datetime.strptime(op.cell(o.username, 4).inner_text().strip(), F.LAST_LOGIN_FORMAT)
        assert abs(shown - logged_in_at) <= timedelta(minutes=F.LOGIN_TOLERANCE_MINUTES), shown

    with allure.step("Verify the Audit log records ADMIN_ACTIVATE"):
        expect(_audit_entries(op.page, F.AUDIT_ACTIVATED, f"ID #{o.id}")).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-275 / TC-276  Delete
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-275")
@allure.story(STORY)
@allure.title("TC-275: Delete asks for confirmation; Cancel keeps the officer")
def test_tc275_delete_cancel(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given a new test officer exists
    When  I click Delete and Cancel "Delete this officer account permanently? This cannot be undone."
    Then  the officer is still listed

    AIO: KAN-TC-275 | KAN-34 AC-10 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()

    with allure.step("Click Delete and Cancel"):
        assert op.delete(o.username, action="dismiss") == F.CONFIRM_DELETE

    with allure.step("Verify the officer is still listed"):
        expect(op.row(o.username)).to_have_count(1)
        assert op.find_officer(o.username)


@aio_case("KAN-TC-276")
@allure.story(STORY)
@allure.title("TC-276: Confirming Delete removes the officer, ends their session and records Admin Deleted")
def test_tc276_delete(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given a new test officer is logged in in another browser
    When  I click Delete and OK
    Then  "Account deleted." is shown, the row disappears, a search finds nothing, the officer cannot log in,
          the Audit log records Admin Deleted and ADMIN_LOGIN_FAILED, and their open session is ended

    AIO: KAN-TC-276 | KAN-34 AC-10, EC-2, EC-3 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()

    with allure.step("Log the test officer in in another browser"):
        officer_page, error = officer_login(o)
        assert not error, error

    with allure.step("Click Delete and OK"):
        assert op.delete(o.username) == F.CONFIRM_DELETE
        expect(op.toast).to_have_text(F.DELETED)
        expect(op.row(o.username)).to_have_count(0)

    with allure.step("Search for the officer"):
        op.search(o.username)
        expect(op.empty_row).to_be_visible()

    with allure.step("Try to log in as the deleted officer"):
        _, error = officer_login(o)
        assert error == F.LOGIN_REFUSED, error

    with allure.step("Verify the Audit log"):
        deleted = _audit_entries(op.page, F.AUDIT_DELETED, f"ID #{o.id}")
        expect(deleted).to_have_count(1)
        expect(deleted).to_contain_text(o.username)
        expect(_audit_entries(op.page, F.AUDIT_LOGIN_FAILED, o.username).first).to_be_visible()

    with allure.step("Reload the officer's open page in the other browser"):
        officer_page.reload()
        expect(officer_page).to_have_url(LOGIN_URL)


# ---------------------------------------------------------------------------
# TC-277 / TC-278  Username and password rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-277")
@allure.story(STORY)
@allure.title("TC-277: Username rules are enforced on the Add officer form")
def test_tc277_username_rules(logged_in_officers_page: OfficersPage):
    """
    Given the Add officer dialog is open
    When  I type usernames that are too short, start with a digit, use other characters or repeat dots
    Then  each shows its message; spaces cannot be typed; at most 30 characters are accepted; a blank username
          on Save shows "Username is required."; a valid username turns the field green

    AIO: KAN-TC-277 | KAN-34 field-level validation (Username) | nothing is saved
    """
    op = logged_in_officers_page
    op.open_add_form()

    for typed, key in F.USERNAME_CASES:
        with allure.step(f"Type '{typed}'"):
            op.type_into(op.username_input, typed)
            expect(op.field_error("username")).to_have_text(F.MSG[key])

    with allure.step("Type a username with a space"):
        op.username_input.fill("qa test")
        expect(op.username_input).to_have_value("qatest")

    with allure.step("Type 31 characters"):
        op.username_input.fill("")
        op.username_input.press_sequentially("a" * 31)
        expect(op.username_input).to_have_value("a" * 30)

    with allure.step("Clear the username and click Save"):
        op.username_input.fill("")
        op.save(expect_saved=False)
        expect(op.field_error("username")).to_have_text(F.MSG["user_required"])
        expect(op.form_error).to_have_text(F.FORM_ERROR)

    with allure.step(f"Type '{F.VALID_USERNAME}'"):
        op.type_into(op.username_input, F.VALID_USERNAME)
        expect(op.field_error("username")).to_have_text("")
        expect(op.field_box("username")).to_have_class(re.compile(r"\bis-valid\b"))


@aio_case("KAN-TC-278")
@allure.story(STORY)
@allure.title("TC-278: Password rules, checklist and Confirm password are enforced on the Add officer form")
def test_tc278_password_rules(logged_in_officers_page: OfficersPage, officers_data):
    """
    Given the Add officer dialog is open with username qatest01 and mobile 9876543210
    When  I type weak passwords, a valid one, and confirmations
    Then  each rule shows its message, the checklist and strength bar follow, SHOW reveals the password,
          paste into Confirm password is blocked, and mismatched / missing confirmations and passwords are refused

    AIO: KAN-TC-278 | KAN-34 field-level validation (Password, Confirm password) | nothing is saved
    """
    op = logged_in_officers_page
    valid = officers_data.district_officer().password
    op.open_add_form()
    op.type_into(op.username_input, F.PW_CONTEXT_USERNAME)
    op.type_into(op.mobile_input, F.PW_CONTEXT_MOBILE)

    with allure.step("Type a password without an uppercase letter or special character"):
        op.type_into(op.password_input, F.PASSWORD_NO_UPPER_SPECIAL)
        expect(op.field_error("password")).to_have_text(F.MSG["pw_mix"])
        expect(op.password_rules_met).to_have_text(["8–64 characters", "1 lowercase letter", "1 number", "No spaces"])
        expect(op.password_bar).to_have_css("background-color", F.BAR_ORANGE)

    for pw, key in F.PASSWORD_CASES:
        with allure.step(f"Type a password that breaks '{key}'"):
            op.type_into(op.password_input, pw)
            expect(op.field_error("password")).to_have_text(F.MSG[key])

    with allure.step("Type a valid password and click SHOW"):
        op.type_into(op.password_input, valid)
        expect(op.field_error("password")).to_have_text("")
        expect(op.password_rules_met).to_have_count(len(F.PASSWORD_RULES))
        expect(op.password_bar).to_have_css("background-color", F.BAR_GREEN)
        op.password_show_button.click()
        expect(op.password_input).to_have_attribute("type", "text")
        expect(op.password_show_button).to_have_text("HIDE")

    with allure.step("Try to paste into Confirm password"):
        assert op.dispatch_paste(op.confirm_input), "Paste into Confirm password was not blocked"

    with allure.step("Type a different confirmation"):
        op.type_into(op.confirm_input, valid + "x")
        expect(op.field_error("confirm")).to_have_text(F.MSG["confirm_mismatch"])

    with allure.step("Clear Confirm password and click Save"):
        op.confirm_input.fill("")
        op.save(expect_saved=False)
        expect(op.field_error("confirm")).to_have_text(F.MSG["confirm_required"])

    with allure.step("Clear both password fields and click Save"):
        op.password_input.fill("")
        op.save(expect_saved=False)
        expect(op.field_error("password")).to_have_text(F.MSG["pw_required"])


# ---------------------------------------------------------------------------
# TC-279  Last login
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-279")
@allure.story(STORY)
@allure.title("TC-279: Last login shows Never for a new officer and the login time after they log in")
def test_tc279_last_login(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given a new test officer has never logged in
    Then  Last login shows "Never"
    When  they log in
    Then  Last login shows that date and time (IST) as YYYY-MM-DD HH:MM:SS

    AIO: KAN-TC-279 | KAN-34 AC-12 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()

    with allure.step("Verify Last login is 'Never'"):
        expect(op.cell(o.username, 4)).to_have_text(F.NEVER)

    with allure.step("Log in as the officer in another browser"):
        _, error = officer_login(o)
        assert not error, error
        logged_in_at = _now_ist()

    with allure.step("Reload and verify Last login"):
        op.open()
        text = op.cell(o.username, 4).inner_text().strip()
        allure.attach(f"shown {text}, IST now {logged_in_at:%Y-%m-%d %H:%M:%S}", name="last login")
        assert abs(datetime.strptime(text, F.LAST_LOGIN_FORMAT) - logged_in_at) <= timedelta(minutes=F.LOGIN_TOLERANCE_MINUTES)


# ---------------------------------------------------------------------------
# TC-725 … TC-727  Other roles
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-725")
@allure.story(STORY)
@allure.title("TC-725: A Commissioner sees every officer except Super Administrators and manages Divisional and District Officers")
def test_tc725_commissioner_view(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given new test officers: a Commissioner C and a District Officer D
    When  C opens Officers & Access
    Then  no Super Administrator is listed, Commissioner rows have no buttons, D has Edit and Deactivate,
          no Delete button exists, Add officer offers Divisional / District Officer, and there is no Legacy link

    AIO: KAN-TC-725 | KAN-34 AC-2 | data: new commissioner + new district officer
    """
    c = new_officers.create(officers_data.commissioner())
    d = new_officers.create(officers_data.district_officer())

    with allure.step("Log in as C and open Officers & Access"):
        cp, error = officer_login(c)
        assert not error, error
        view = OfficersPage(cp)
        view.open()

    with allure.step("Verify the list"):
        rows = _rows_summary(view)
        assert not [r for r in rows if r["role"] == F.ROLE_LABELS["superadmin"]]
        assert all(r["buttons"] == [] for r in rows if r["role"] == F.ROLE_LABELS["commissioner"])
        assert _buttons(view.row(d.username).first) == ["Edit", "Deactivate"]
        assert not [r for r in rows if "Delete" in r["buttons"]]

    with allure.step("Open Add officer and look at Role"):
        view.open_add_form()
        expect(view.role_select.locator("option")).to_have_text(
            [F.ROLE_LABELS["division"], F.ROLE_LABELS["district"]])

    with allure.step("Verify the sidebar has no Legacy admin tools link"):
        expect(AdminSidebar(cp).admin_users_link).to_have_count(0)


@aio_case("KAN-TC-726")
@allure.story(STORY)
@allure.title("TC-726: A Divisional Officer sees only their division and manages its District Officers")
def test_tc726_divisional_view(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given new test officers: a Divisional Officer B (Pune) and a District Officer D (Pune)
    When  B opens Officers & Access
    Then  only Pune division's Divisional and District Officers are listed, D has Edit and Deactivate (no
          Delete), and Add officer offers only District Officer in Pune

    AIO: KAN-TC-726 | KAN-34 AC-2 | data: new divisional officer + new district officer
    """
    b = new_officers.create(officers_data.divisional_officer())
    d = new_officers.create(officers_data.district_officer())

    with allure.step("Log in as B and open Officers & Access"):
        bp, error = officer_login(b)
        assert not error, error
        view = OfficersPage(bp)
        view.open()

    with allure.step("Verify only Pune division is listed"):
        listed = view.list_officers()
        assert listed and {o["division_name"] for o in listed} == {b.division}, {o["division_name"] for o in listed}
        assert {o["role"] for o in listed} <= {"division", "district"}
        expect(view.officer_rows).to_have_count(len(listed))

    with allure.step("Verify D's buttons and that no Delete button exists"):
        assert _buttons(view.row(d.username).first) == ["Edit", "Deactivate"]
        expect(view.page.locator("#rows button", has_text="Delete")).to_have_count(0)

    with allure.step("Open Add officer"):
        view.open_add_form()
        expect(view.role_select.locator("option")).to_have_text([F.ROLE_LABELS["district"]])
        expect(view.division_select.locator("option")).to_have_text(["Select division", b.division])


@aio_case("KAN-TC-727")
@allure.story(STORY)
@allure.title("TC-727: A District Officer has no access to Officers & Access")
def test_tc727_district_no_access(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given a new test District Officer D is logged in
    Then  the sidebar has no Officers & access link
    When  D opens the Officers & Access URL
    Then  "Access denied — this page is for Divisional Officer and above." is shown and no list

    AIO: KAN-TC-727 | KAN-34 AC-2 | data: new district officer
    """
    d = new_officers.create(officers_data.district_officer())

    with allure.step("Log in as D"):
        dp, error = officer_login(d)
        assert not error, error
        dp.goto(ADMIN_DASHBOARD_URL)
        expect(AdminSidebar(dp).officers_link).to_have_count(0)

    with allure.step("Open the Officers & Access URL"):
        dp.goto(OFFICERS_URL)
        expect(dp.get_by_text(F.ACCESS_DENIED)).to_be_visible()
        expect(dp.locator("#rows tr")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-728  Role → area fields
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-728")
@allure.story(STORY)
@allure.title("TC-728: The chosen role shows only the area fields it needs")
def test_tc728_role_area_fields(logged_in_officers_page: OfficersPage):
    """
    Given the Add officer dialog is open
    Then  Commissioner (State) is chosen and Division / District are hidden
    When  I choose Divisional Officer, then District Officer, Save, and choose Nashik, then Super Administrator
    Then  Division (then District) appear, the missing area is reported, District lists Nashik's districts,
          and both hide again

    AIO: KAN-TC-728 | KAN-34 AC-5 | nothing is saved
    """
    op = logged_in_officers_page
    op.open_add_form()

    with allure.step("Look at the default role"):
        expect(op.role_select.locator("option:checked")).to_have_text(F.DEFAULT_ROLE)
        expect(op.division_field).to_be_hidden()
        expect(op.district_field).to_be_hidden()

    with allure.step("Choose Divisional Officer"):
        op.choose_role(F.ROLE_LABELS["division"])
        expect(op.division_field).to_be_visible()
        expect(op.division_select.locator("option")).to_have_text(F.DIVISIONS)
        expect(op.district_field).to_be_hidden()

    with allure.step("Choose District Officer and click Save"):
        op.choose_role(F.ROLE_LABELS["district"])
        expect(op.district_field).to_be_visible()
        expect(op.district_select.locator("option")).to_have_text([F.DISTRICT_PLACEHOLDER])
        op.save(expect_saved=False)
        expect(op.field_error("division_id")).to_have_text(F.MSG["division"])
        expect(op.field_error("district_id")).to_have_text(F.MSG["district"])

    with allure.step("Choose Division Nashik"):
        op.choose_division("Nashik")
        expect(op.district_select.locator("option")).to_have_text(["Select district"] + F.NASHIK_DISTRICTS)

    with allure.step("Choose Super Administrator"):
        op.choose_role(F.ROLE_LABELS["superadmin"])
        expect(op.division_field).to_be_hidden()
        expect(op.district_field).to_be_hidden()


# ---------------------------------------------------------------------------
# TC-729  Edit
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-729")
@allure.story(STORY)
@allure.title("TC-729: Edit officer saves changes and keeps the password when both password fields are blank")
def test_tc729_edit(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given a new test officer exists
    When  I click Edit
    Then  "Edit officer" opens with their details, empty optional password fields and the keep-password help
    When  I change the designation and Save
    Then  "Account updated." is shown, the row shows the change, the old password still works and the Audit
          log records ADMIN_UPDATE

    AIO: KAN-TC-729 | KAN-34 AC-6 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()

    with allure.step("Click Edit"):
        op.open_edit_form(o.username)
        expect(op.dialog_title).to_have_text(F.EDIT_TITLE)
        expect(op.role_select).to_have_value(o.role)
        expect(op.division_select.locator("option:checked")).to_have_text(o.division)
        expect(op.district_select.locator("option:checked")).to_have_text(o.district)
        expect(op.full_name_input).to_have_value(o.full_name)
        expect(op.designation_input).to_have_value(o.designation)
        expect(op.username_input).to_have_value(o.username)
        expect(op.email_input).to_have_value(o.email)
        expect(op.mobile_input).to_have_value(o.mobile)
        expect(op.password_input).to_have_value("")
        expect(op.password_required_mark).to_be_hidden()
        expect(op.password_help).to_have_text(F.KEEP_PASSWORD_HELP)

    with allure.step("Change the designation and click Save"):
        op.type_into(op.designation_input, "QA Lead")
        op.save()
        expect(op.toast).to_have_text(F.UPDATED)
        expect(op.officer_sub_line(o.username)).to_have_text(f"{o.username} · QA Lead")

    with allure.step("Log in with the original password"):
        _, error = officer_login(o)
        assert not error, error

    with allure.step("Verify the Audit log records ADMIN_UPDATE"):
        expect(_audit_entries(op.page, F.AUDIT_UPDATED, f"ID #{o.id}").first).to_be_visible()


# ---------------------------------------------------------------------------
# TC-730  Search
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-730")
@allure.story(STORY)
@allure.title("TC-730: Search lists officers whose name, username, email, division or district matches")
def test_tc730_search(logged_in_officers_page: OfficersPage):
    """
    Given I am on Officers & Access
    When  I search for 'pune', 'PUNE', part of an email and text that matches nobody, then clear the box
    Then  only matching officers are listed (any letter case), "No officers found." for no match, and everyone
          again when cleared

    AIO: KAN-TC-730 | KAN-34 AC-11 | data: existing officers (read only)
    """
    op = logged_in_officers_page
    total = op.officer_rows.count()

    with allure.step(f"Search for '{F.SEARCH_TERM}'"):
        op.search(F.SEARCH_TERM)
        texts = op.row_texts()
        assert texts and all(F.SEARCH_TERM in t.lower() for t in texts), texts
        found = len(texts)

    with allure.step(f"Search for '{F.SEARCH_TERM.upper()}'"):
        op.search(F.SEARCH_TERM.upper())
        expect(op.officer_rows).to_have_count(found)

    with allure.step(f"Search for '{F.EMAIL_PART}'"):
        op.search(F.EMAIL_PART)
        expect(op.officer_rows).to_have_count(1)
        expect(op.officer_rows.first).to_contain_text(F.EMAIL_PART)

    with allure.step(f"Search for '{F.NO_MATCH}'"):
        op.search(F.NO_MATCH)
        expect(op.empty_row).to_have_text(F.EMPTY_LIST)

    with allure.step("Clear the box"):
        op.search("")
        expect(op.officer_rows).to_have_count(total)


# ---------------------------------------------------------------------------
# TC-731 … TC-733  Other field rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-731")
@allure.story(STORY)
@allure.title("TC-731: Full name and Designation rules are enforced on the Add officer form")
def test_tc731_name_designation_rules(logged_in_officers_page: OfficersPage):
    """
    Given the Add officer dialog is open
    Then  only letters, spaces, . ' - can be typed in Full name; short or badly ending names, a blank name,
          a 1-character or symbol designation are refused; extra spaces are removed; Designation stops at 100

    AIO: KAN-TC-731 | KAN-34 field-level validation (Full name, Designation) | nothing is saved
    """
    op = logged_in_officers_page
    op.open_add_form()

    with allure.step(f"Type '{F.NAME_TYPED}' in Full name"):
        op.full_name_input.fill(F.NAME_TYPED)
        expect(op.full_name_input).to_have_value(F.NAME_KEPT)

    for typed, key in F.NAME_CASES:
        with allure.step(f"Type '{typed}' in Full name"):
            op.type_into(op.full_name_input, typed)
            expect(op.field_error("full_name")).to_have_text(F.MSG[key])

    with allure.step("Type a name with extra spaces and leave the field"):
        op.type_into(op.full_name_input, F.NAME_SPACED)
        expect(op.full_name_input).to_have_value(F.NAME_TIDY)

    with allure.step("Clear Full name and click Save"):
        op.full_name_input.fill("")
        op.save(expect_saved=False)
        expect(op.field_error("full_name")).to_have_text(F.MSG["name_required"])

    for typed, key in F.DESIG_CASES:
        with allure.step(f"Type '{typed}' in Designation"):
            op.type_into(op.designation_input, typed)
            expect(op.field_error("designation")).to_have_text(F.MSG[key])

    with allure.step("Type 101 characters in Designation"):
        op.designation_input.fill("")
        op.designation_input.press_sequentially("a" * 101)
        expect(op.designation_input).to_have_value("a" * 100)


@aio_case("KAN-TC-732")
@allure.story(STORY)
@allure.title("TC-732: Official email and Mobile number rules are enforced on the Add officer form")
def test_tc732_email_mobile_rules(logged_in_officers_page: OfficersPage):
    """
    Given the Add officer dialog is open
    Then  invalid emails and a blank email are refused; only digits can be typed in Mobile number; a short
          number, one not starting 6–9, one digit repeated and a blank number are refused

    AIO: KAN-TC-732 | KAN-34 field-level validation (Official email, Mobile number) | nothing is saved
    """
    op = logged_in_officers_page
    op.open_add_form()

    for typed in F.EMAIL_CASES:
        with allure.step(f"Type '{typed}' in Official email"):
            op.type_into(op.email_input, typed)
            expect(op.field_error("email")).to_have_text(F.MSG["email_invalid"])

    with allure.step("Clear Official email and click Save"):
        op.email_input.fill("")
        op.save(expect_saved=False)
        expect(op.field_error("email")).to_have_text(F.MSG["email_required"])

    with allure.step(f"Type '{F.MOBILE_TYPED}' in Mobile number"):
        op.mobile_input.fill(F.MOBILE_TYPED)
        expect(op.mobile_input).to_have_value(F.MOBILE_KEPT)

    for typed, key in F.MOBILE_CASES:
        with allure.step(f"Type '{typed}' in Mobile number"):
            op.type_into(op.mobile_input, typed)
            expect(op.field_error("mobile")).to_have_text(F.MSG[key].format(n=len(typed)))

    with allure.step("Clear Mobile number and click Save"):
        op.mobile_input.fill("")
        op.save(expect_saved=False)
        expect(op.field_error("mobile")).to_have_text(F.MSG["mobile_required"])


@aio_case("KAN-TC-733")
@allure.story(STORY)
@allure.title("TC-733: Saving an empty District Officer form shows every required-field message")
def test_tc733_empty_form(logged_in_officers_page: OfficersPage):
    """
    Given the Add officer dialog is open
    When  I choose District Officer and click Save without entering anything
    Then  "Please correct the highlighted fields." and each required-field message are shown, Designation has
          none and the cursor is in Division; after Cancel the dialog opens empty

    AIO: KAN-TC-733 | KAN-34 field-level validation | nothing is saved
    """
    op = logged_in_officers_page
    expected = {"division_id": F.MSG["division"], "district_id": F.MSG["district"], "full_name": F.MSG["name_required"],
                "designation": "", "username": F.MSG["user_required"], "email": F.MSG["email_required"],
                "mobile": F.MSG["mobile_required"], "password": F.MSG["pw_required"]}

    with allure.step("Choose District Officer and click Save"):
        op.open_add_form()
        op.choose_role(F.ROLE_LABELS["district"])
        op.save(expect_saved=False)
        expect(op.form_error).to_have_text(F.FORM_ERROR)
        for name, msg in expected.items():
            expect(op.field_error(name)).to_have_text(msg)
        expect(op.division_select).to_be_focused()

    with allure.step("Click Cancel and open Add officer again"):
        op.cancel_button.click()
        expect(op.dialog).not_to_have_class(OPEN)
        op.open_add_form()
        expect(op.role_select.locator("option:checked")).to_have_text(F.DEFAULT_ROLE)
        expect(op.form_error).to_be_hidden()
        expect(op.page.locator("#frmBody .has-error")).to_have_count(0)
        expect(op.full_name_input).to_have_value("")


# ---------------------------------------------------------------------------
# TC-734 / TC-735  Server-side rules
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-734")
@allure.story(STORY)
@allure.title("TC-734: The server refuses what the form refuses")
def test_tc734_server_rules(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given save requests are sent straight to the API, bypassing the form
    When  they carry a 4-character username, a username starting with a digit, digits in the name, the password
          "password", or a password containing the username
    Then  each is refused and no account is created; a username with a space gets a username message only

    AIO: KAN-TC-734 | KAN-34 EC-1 | data: new district officers (any created by mistake are deleted)
    """
    op = logged_in_officers_page
    base = officers_data.district_officer()
    accepted, problems = [], []

    for label, data in F.server_bypass_cases(base).items():
        with allure.step(f"Send a save with a {label}"):
            res = op.api("admins.save", op.save_payload(data))
            allure.attach(str(res), name=label)
            if res["ok"]:
                new_officers.track_id(res["data"]["id"], data.username)
                accepted.append(label)

    with allure.step("Send a save with a username containing a space"):
        spaced = replace(base, username="qa test")
        res = op.api("admins.save", op.save_payload(spaced))
        allure.attach(str(res), name="username with a space")
        if res["ok"]:
            new_officers.track_id(res["data"]["id"], spaced.username)
            accepted.append("username with a space")
        elif F.SERVER_SPACE_USERNAME_MESSAGE_BAD in res["msg"]:
            problems.append(f"username with a space: '{res['msg']}'")

    with allure.step("Verify every request was refused"):
        if accepted:
            problems.insert(0, "accepted: " + ", ".join(accepted))
        assert not problems, "; ".join(problems)


@aio_case("KAN-TC-735")
@allure.story(STORY)
@allure.title("TC-735: Commissioners and Divisional Officers cannot delete officers through the API")
def test_tc735_lower_role_delete_refused(logged_in_officers_page: OfficersPage, new_officers, officer_login, officers_data):
    """
    Given new test officers: a Divisional Officer B (Pune) and a District Officer D (Pune)
    When  B sends a delete request for D
    Then  it is refused with "Your role cannot perform this action." and D is still listed

    AIO: KAN-TC-735 | KAN-34 EC-4 | data: new divisional officer + new district officer
    """
    op = logged_in_officers_page
    b = new_officers.create(officers_data.divisional_officer())
    d = new_officers.create(officers_data.district_officer())

    with allure.step("Log in as B and send a delete for D"):
        bp, error = officer_login(b)
        assert not error, error
        view = OfficersPage(bp)
        view.open()
        res = view.api("admins.delete", {"id": d.id})
        assert not res["ok"] and res["msg"] == F.ROLE_REFUSED, res

    with allure.step("Verify D is still listed"):
        assert op.find_officer(d.username)


# ---------------------------------------------------------------------------
# TC-736 / TC-737  Search edge cases
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-736")
@allure.story(STORY)
@allure.title("TC-736: Search treats % and _ as plain characters")
def test_tc736_search_wildcards(logged_in_officers_page: OfficersPage):
    """
    Given I am on Officers & Access
    When  I search for % and for _
    Then  only officers whose details contain that character are listed ("No officers found." if none)

    AIO: KAN-TC-736 | KAN-34 EC-5 | data: existing officers (read only)
    """
    op = logged_in_officers_page
    for ch in F.WILDCARDS:
        with allure.step(f"Search for '{ch}'"):
            op.search(ch)
            matches = [o for o in op.list_officers(ch)]
            listed = op.row_texts()
            allure.attach(f"{len(listed)} listed", name=f"search {ch}")
            wrong = [o["username"] for o in matches if not any(ch in str(o[k] or "") for k in
                     ("full_name", "username", "email", "designation", "district_name", "division_name"))]
            assert not wrong, f"'{ch}' lists {len(wrong)} officers without '{ch}', e.g. {wrong[:3]}"


@aio_case("KAN-TC-737")
@allure.story(STORY)
@allure.title("TC-737: Search text with quotes or HTML is handled safely")
def test_tc737_search_special_text(logged_in_officers_page: OfficersPage):
    """
    Given I am on Officers & Access
    When  I search for O'Brien and <b>x</b>
    Then  the box keeps the text, "No officers found." is shown and nothing is rendered in bold

    AIO: KAN-TC-737 | KAN-34 EC-6
    """
    op = logged_in_officers_page
    for text in F.SPECIAL_SEARCHES:
        with allure.step(f"Search for {text}"):
            op.search(text)
            expect(op.search_input).to_have_value(text)
            expect(op.empty_row).to_have_text(F.EMPTY_LIST)
            expect(op.page.locator("#rows b")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-738 … TC-740  Form edge cases
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-738")
@allure.story(STORY)
@allure.title("TC-738: Changing a District Officer to Commissioner clears the division and district")
def test_tc738_role_change_clears_area(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given a new test District Officer (Pune / Pune)
    When  I edit them, change the role to Commissioner (State) and Save
    Then  "Account updated." is shown and they are listed as Commissioner (State), area Maharashtra, with no
          division or district saved

    AIO: KAN-TC-738 | KAN-34 EC-7 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()

    with allure.step("Click Edit"):
        op.open_edit_form(o.username)
        expect(op.district_select.locator("option:checked")).to_have_text(o.district)

    with allure.step("Change the role to Commissioner (State) and click Save"):
        op.choose_role(F.ROLE_LABELS["commissioner"])
        op.save()
        expect(op.toast).to_have_text(F.UPDATED)

    with allure.step("Verify the officer's row"):
        expect(op.role_badge(o.username)).to_have_text(F.ROLE_LABELS["commissioner"])
        expect(op.cell(o.username, 2)).to_have_text("Maharashtra")
        saved = op.find_officer(o.username)
        assert (saved["division_id"], saved["district_id"]) == (None, None), saved


@aio_case("KAN-TC-739")
@allure.story(STORY)
@allure.title("TC-739: Extra spaces are removed and the email is saved in lower case")
def test_tc739_tidy_values(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given I add a District Officer with extra spaces in Full name and Designation and the email in capitals
    Then  they are saved as "QA Test", "QA Lead" and the email in lower case

    AIO: KAN-TC-739 | KAN-34 EC-8 | data: new district officer
    """
    op = logged_in_officers_page
    o = officers_data.district_officer(full_name=F.SPACED_NAME, designation=F.SPACED_DESIG)
    o.email = o.email.upper()

    with allure.step("Add the officer"):
        op.open_add_form()
        op.fill_form(o)
        op.save()
        expect(op.toast).to_have_text(F.created_toast(o))
        new_officers.track(o)

    with allure.step("Verify the saved values"):
        expect(op.cell(o.username, 0).locator("strong")).to_have_text("QA Test")
        expect(op.officer_sub_line(o.username)).to_have_text(f"{o.username} · QA Lead")
        expect(op.cell(o.username, 3)).to_contain_text(o.email.lower())


@aio_case("KAN-TC-740")
@allure.story(STORY)
@allure.title("TC-740: Closing the officer dialog without saving discards the changes")
def test_tc740_close_discards(logged_in_officers_page: OfficersPage, new_officers, officers_data):
    """
    Given a new test officer exists
    When  I close the Add / Edit dialog with Close, Escape, a click outside it or Cancel after typing
    Then  nothing is saved and the form opens empty (Add) or with the saved values (Edit) next time

    AIO: KAN-TC-740 | KAN-34 EC-9 | data: new_district_officer
    """
    op = logged_in_officers_page
    o = new_officers.create(officers_data.district_officer())
    op.open()
    before = op.officer_rows.count()

    with allure.step("Type a name in Add officer and click Close"):
        op.open_add_form()
        op.type_into(op.full_name_input, "Qa Discard")
        op.close_button.click()
        expect(op.dialog).not_to_have_class(OPEN)
        expect(op.officer_rows).to_have_count(before)

    with allure.step("Open Add officer again"):
        op.open_add_form()
        expect(op.full_name_input).to_have_value("")
        op.cancel_button.click()

    with allure.step("Edit the officer, change the designation and press Escape"):
        op.open_edit_form(o.username)
        op.type_into(op.designation_input, "Changed")
        op.page.keyboard.press("Escape")
        expect(op.dialog).not_to_have_class(OPEN)

    with allure.step("Edit again, change the designation and click outside the dialog"):
        op.open_edit_form(o.username)
        op.type_into(op.designation_input, "Changed")
        op.dialog.click(position={"x": 5, "y": 5})
        expect(op.dialog).not_to_have_class(OPEN)

    with allure.step("Edit again and click Cancel"):
        op.open_edit_form(o.username)
        expect(op.designation_input).to_have_value(o.designation)
        op.cancel_button.click()

    with allure.step("Verify nothing changed"):
        expect(op.officer_sub_line(o.username)).to_have_text(f"{o.username} · {o.designation}")
        assert op.find_officer(o.username)["designation"] == o.designation
