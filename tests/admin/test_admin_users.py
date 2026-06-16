"""
Admin User Management — Super Admin Portal
==========================================
Covers KAN-TC-268 through KAN-TC-279 for the Admin Users page
(/module/admin/admins/index.php).

Safety / data handling:

* Create tests use accounts with run-unique usernames/emails and remove them on
  teardown via the ``created_admins`` cleanup fixture, so the dev environment
  doesn't accumulate test accounts.
* Toggle and delete tests act on a self-contained ``throwaway_admin`` (created
  fresh, deleted on teardown) — no shared dev account is ever mutated.
* Duplicate-conflict tests (TC-271/272) read a REAL existing username/email from
  the live table rather than the AIO sheet's fixed ``officer01`` /
  ``priya@mppa.gov`` (which describe the spec dataset). The duplicate-username
  case deliberately does NOT register cleanup, so a failure can never delete the
  genuine account it collided with.

Assumptions worth knowing:

* Server-side validation / duplicate errors are expected to render as the shared
  admin error banner (``.salt-e`` → ``error_alert``). Each such test ALSO asserts
  the account count is unchanged, which holds regardless of the banner markup.
* Deactivation/deletion's downstream effects (login blocked, live session
  terminated, audit-log entry) are the documented intent but are asserted here
  through their reliable UI projection — the persisted toggle state and the row's
  removal. End-to-end login/session verification is out of scope (admin login is
  CAPTCHA-gated and would make these tests flaky).
"""

import re

import allure
import pytest
from playwright.sync_api import expect

from pages.admin.users_page import AdminUsersPage
from test_data.admin_users_factory import AdminUserData, AdminUsersFactory
from utils.aio import aio_case


# ---------------------------------------------------------------------------
# TC-268  All admin accounts are listed with full metadata
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-268")
@allure.story("Admin User Management")
@allure.title("TC-268: All admin accounts are listed with full metadata")
def test_tc268_all_admins_listed_with_metadata(
    logged_in_admin_users_page: AdminUsersPage,
):
    """
    Given I am logged in as Super Admin on Admin User Management
    When  the page loads
    Then  the heading reads 'Admin User Management (N)'
    And   N matches the number of table rows
    And   every row shows username, full name, email, role badge and an
          active toggle

    AIO: KAN-TC-268 | data: live table state
    """
    sp = logged_in_admin_users_page

    with allure.step("Verify the heading shows the admin count"):
        expect(sp.page_title).to_contain_text("Admin User Management")
        count = sp.get_title_count()

    with allure.step("Verify the table lists exactly that many admin rows"):
        expect(sp.admin_rows.first).to_be_visible()
        assert sp.admin_rows.count() == count, (
            f"Heading says ({count}) but the table has {sp.admin_rows.count()} rows."
        )

    for i in range(sp.admin_rows.count()):
        username = sp.get_username_of_row(sp.admin_rows.nth(i))
        with allure.step(f"Verify row {i + 1} ('{username}') is fully populated"):
            assert username, f"Row {i + 1} has an empty username."
            expect(sp.full_name_cell(username)).not_to_be_empty()
            expect(sp.email_cell(username)).to_contain_text("@")
            expect(sp.role_badge(username)).to_be_visible()
            expect(sp.active_toggle(username)).to_have_count(1)


# ---------------------------------------------------------------------------
# TC-269  Super Admin row is protected (no toggle / delete / perms)
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-269")
@allure.story("Admin User Management")
@allure.title("TC-269: Super Admin row shows 'Protected' with toggle and delete locked")
def test_tc269_superadmin_row_protected(
    logged_in_admin_users_page: AdminUsersPage,
):
    """
    Given the Admin Users list
    When  I locate the Super Admin row (by its role badge)
    Then  its Actions cell shows 'Protected'
    And   its Active toggle is disabled
    And   it has no Perms or Delete button

    AIO: KAN-TC-269 | data: the superadmin-role account
    """
    sp = logged_in_admin_users_page

    with allure.step("Locate the Super Admin row by its role badge"):
        expect(sp.superadmin_row).to_have_count(1)
        su = sp.get_username_of_row(sp.superadmin_row)

    with allure.step("Verify the Actions cell shows 'Protected'"):
        expect(sp.protected_label(su)).to_be_visible()

    with allure.step("Verify the Active toggle is disabled"):
        expect(sp.active_toggle(su)).to_be_disabled()

    with allure.step("Verify no Perms or Delete button is present on this row"):
        expect(sp.permissions_button(su)).to_have_count(0)
        expect(sp.delete_button(su)).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-270  Creating a new admin adds it to the list immediately
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-270")
@allure.story("Admin User Management")
@allure.title("TC-270: Creating a valid admin adds it to the list immediately")
def test_tc270_create_admin(
    logged_in_admin_users_page: AdminUsersPage,
    created_admins,
    new_admin_data: AdminUserData,
):
    """
    Given the Admin Users list
    When  I open Create Admin, fill all required fields with a unique username
          and email, and submit
    Then  the new account appears in the table with its metadata
    And   the heading count increments by one

    AIO: KAN-TC-270 | data: new_admin (run-unique)
    """
    sp = logged_in_admin_users_page
    data = new_admin_data

    with allure.step("Record the current admin count"):
        before = sp.get_title_count()

    with allure.step(f"Create admin '{data.username}' (role: {data.role})"):
        sp.create_admin(
            data.username, data.full_name, data.email, data.password,
            role=data.role, permissions=data.permissions,
        )
        sp.wait_for_load()
        created_admins(data.username)

    with allure.step("Verify the new account appears with its metadata"):
        expect(sp.admin_row(data.username)).to_be_visible()
        expect(sp.full_name_cell(data.username)).to_have_text(data.full_name)
        expect(sp.email_cell(data.username)).to_contain_text(data.email)
        expect(sp.role_badge(data.username)).to_contain_text(data.role)

    with allure.step("Verify the heading count incremented by one"):
        expect(sp.page_title).to_contain_text(f"({before + 1})")


# ---------------------------------------------------------------------------
# TC-271  Duplicate username is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-271")
@allure.story("Admin User Management")
@allure.title("TC-271: Creating an admin with an existing username is rejected")
def test_tc271_duplicate_username_rejected(
    logged_in_admin_users_page: AdminUsersPage,
):
    """
    Given an admin account already exists
    When  I try to create a new admin reusing that username (unique email)
    Then  a duplicate error is shown and no new account is created

    No cleanup is registered here: the username collides with a real account, so
    deleting by username on teardown could remove the genuine one.

    AIO: KAN-TC-271 | data: duplicate_username (existing username from the table)
    """
    sp = logged_in_admin_users_page

    with allure.step("Read an existing admin's username from the table"):
        if sp.subadmin_rows.count() == 0:
            pytest.skip("No sub-admin account available to source a duplicate username.")
        existing = sp.get_username_of_row(sp.subadmin_rows.first)
        data = AdminUsersFactory.duplicate_username(existing)
        before = sp.get_title_count()

    with allure.step(f"Attempt to create a new admin reusing username '{existing}'"):
        sp.create_admin(
            data.username, data.full_name, data.email, data.password,
            role=data.role, permissions=data.permissions,
        )
        sp.wait_for_load()

    with allure.step("Verify a duplicate error is shown and no account was created"):
        expect(sp.error_alert).to_be_visible()
        expect(sp.page_title).to_contain_text(f"({before})")


# ---------------------------------------------------------------------------
# TC-272  Duplicate email is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-272")
@allure.story("Admin User Management")
@allure.title("TC-272: Creating an admin with an existing email is rejected")
def test_tc272_duplicate_email_rejected(
    logged_in_admin_users_page: AdminUsersPage,
    created_admins,
):
    """
    Given an admin account already exists
    When  I try to create a new admin (unique username) reusing that email
    Then  a duplicate error is shown and no new account is created

    AIO: KAN-TC-272 | data: duplicate_email (existing email from the table)
    """
    sp = logged_in_admin_users_page

    with allure.step("Read an existing admin's email from the table"):
        if sp.subadmin_rows.count() == 0:
            pytest.skip("No sub-admin account available to source a duplicate email.")
        existing_email = sp.get_email_of_row(sp.subadmin_rows.first)
        data = AdminUsersFactory.duplicate_email(existing_email)
        before = sp.get_title_count()

    # Unique username, so it is safe to clean up if the app wrongly creates it.
    created_admins(data.username)

    with allure.step(f"Attempt to create a new admin reusing email '{existing_email}'"):
        sp.create_admin(
            data.username, data.full_name, data.email, data.password,
            role=data.role, permissions=data.permissions,
        )
        sp.wait_for_load()

    with allure.step("Verify a duplicate error is shown and no account was created"):
        expect(sp.error_alert).to_be_visible()
        expect(sp.page_title).to_contain_text(f"({before})")


# ---------------------------------------------------------------------------
# TC-273  Deactivating a sub-admin persists the Inactive state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-273")
@allure.story("Admin User Management")
@allure.title("TC-273: Setting a sub-admin to Inactive saves and persists")
def test_tc273_deactivate_subadmin(
    logged_in_admin_users_page: AdminUsersPage,
    throwaway_admin: AdminUserData,
):
    """
    Given an active sub-admin account
    When  I switch its Active toggle to Inactive
    Then  the row's status label changes to 'Inactive'
    And   the Inactive state persists after a page reload (the stored flag that
          gates the account's login is now off)

    The login-block / session-termination this enables is the documented
    downstream effect; verifying it end-to-end (a second CAPTCHA-gated login) is
    out of scope — the persisted Inactive flag is the reliable signal.

    AIO: KAN-TC-273 | data: throwaway sub-admin
    """
    sp = logged_in_admin_users_page
    user = throwaway_admin

    with allure.step("Confirm the account starts Active"):
        expect(sp.active_status_label(user.username)).to_have_text("Active")

    with allure.step("Toggle the account to Inactive"):
        sp.toggle_admin_active_and_wait(user.username)
        expect(sp.active_status_label(user.username)).to_have_text("Inactive")

    with allure.step("Verify the Inactive state persists after a reload"):
        sp.open()
        expect(sp.active_toggle(user.username)).not_to_be_checked()
        expect(sp.active_status_label(user.username)).to_have_text("Inactive")


# ---------------------------------------------------------------------------
# TC-274  Reactivating a sub-admin persists the Active state
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-274")
@allure.story("Admin User Management")
@allure.title("TC-274: Toggling a deactivated sub-admin back to Active saves and persists")
def test_tc274_reactivate_subadmin(
    logged_in_admin_users_page: AdminUsersPage,
    inactive_throwaway_admin: AdminUserData,
):
    """
    Given a currently Inactive sub-admin account
    When  I switch its Active toggle back to Active
    Then  the row's status label changes to 'Active'
    And   the Active state persists after a page reload (login access restored)

    AIO: KAN-TC-274 | data: throwaway sub-admin (pre-set Inactive)
    """
    sp = logged_in_admin_users_page
    user = inactive_throwaway_admin

    with allure.step("Confirm the account starts Inactive"):
        expect(sp.active_status_label(user.username)).to_have_text("Inactive")

    with allure.step("Toggle the account back to Active"):
        sp.toggle_admin_active_and_wait(user.username)
        expect(sp.active_status_label(user.username)).to_have_text("Active")

    with allure.step("Verify the Active state persists after a reload"):
        sp.open()
        expect(sp.active_toggle(user.username)).to_be_checked()
        expect(sp.active_status_label(user.username)).to_have_text("Active")


# ---------------------------------------------------------------------------
# TC-275  Delete shows a confirmation dialog; Cancel keeps the account
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-275")
@allure.story("Admin User Management")
@allure.title("TC-275: Delete shows a confirmation dialog and Cancel keeps the account")
def test_tc275_delete_confirmation_cancel(
    logged_in_admin_users_page: AdminUsersPage,
    throwaway_admin: AdminUserData,
):
    """
    Given a sub-admin account
    When  I click Delete and CANCEL the confirmation dialog
    Then  the dialog message reads 'Delete this admin?'
    And   the account is NOT removed from the list

    AIO: KAN-TC-275 | data: throwaway sub-admin
    """
    sp = logged_in_admin_users_page
    user = throwaway_admin

    with allure.step("Click Delete and dismiss the confirmation dialog"):
        message = sp.delete_admin(user.username, action="dismiss")
        assert "Delete this admin?" in message, f"Unexpected dialog message: {message!r}"

    with allure.step("Verify the account is still listed"):
        expect(sp.admin_row(user.username)).to_be_visible()


# ---------------------------------------------------------------------------
# TC-276  Confirming deletion removes the account
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-276")
@allure.story("Admin User Management")
@allure.title("TC-276: Confirming deletion removes the account from the list")
def test_tc276_delete_removes_account(
    logged_in_admin_users_page: AdminUsersPage,
    throwaway_admin: AdminUserData,
):
    """
    Given a sub-admin account
    When  I click Delete and CONFIRM the dialog
    Then  the account is removed from the list
    And   the heading count drops by one

    The target's session-termination ('Your account has been removed.') is the
    documented downstream effect; verifying it end-to-end is out of scope —
    removal from the list is the reliable signal.

    AIO: KAN-TC-276 | data: throwaway sub-admin
    """
    sp = logged_in_admin_users_page
    user = throwaway_admin

    with allure.step("Record the count and confirm the account is present"):
        before = sp.get_title_count()
        expect(sp.admin_row(user.username)).to_be_visible()

    with allure.step("Click Delete and confirm the dialog"):
        sp.delete_admin(user.username, action="accept")
        sp.wait_for_load()

    with allure.step("Verify the account is gone and the count dropped by one"):
        expect(sp.admin_row(user.username)).to_have_count(0)
        expect(sp.page_title).to_contain_text(f"({before - 1})")


# ---------------------------------------------------------------------------
# TC-277  Username shorter than 4 characters is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-277")
@allure.story("Admin User Management")
@allure.title("TC-277: Username under 4 characters is rejected on create")
def test_tc277_short_username_rejected(
    logged_in_admin_users_page: AdminUsersPage,
    short_username_data: AdminUserData,
):
    """
    Given the Create Admin form
    When  I submit a username shorter than 4 characters (valid everything else)
    Then  an error is shown and no account is created

    AIO: KAN-TC-277 | data: short_username ('adm')
    """
    sp = logged_in_admin_users_page
    data = short_username_data

    with allure.step("Record the current admin count"):
        before = sp.get_title_count()

    with allure.step(f"Attempt to create an admin with a 3-char username '{data.username}'"):
        sp.create_admin(
            data.username, data.full_name, data.email, data.password,
            role=data.role, permissions=data.permissions,
        )
        sp.wait_for_load()

    with allure.step("Verify an error is shown and no account was created"):
        expect(sp.error_alert).to_be_visible()
        expect(sp.page_title).to_contain_text(f"({before})")


# ---------------------------------------------------------------------------
# TC-278  Password without the required complexity is rejected
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-278")
@allure.story("Admin User Management")
@allure.title("TC-278: Password without required complexity is rejected on create")
def test_tc278_weak_password_rejected(
    logged_in_admin_users_page: AdminUsersPage,
    created_admins,
    weak_password_data: AdminUserData,
):
    """
    Given the Create Admin form
    When  I submit a password that meets the length minimum but lacks an
          uppercase letter and a symbol
    Then  an error is shown and no account is created

    AIO: KAN-TC-278 | data: weak_password ('simple123')
    """
    sp = logged_in_admin_users_page
    data = weak_password_data

    with allure.step("Record the current admin count"):
        before = sp.get_title_count()

    # Unique username — clean up defensively in case the app wrongly accepts it.
    created_admins(data.username)

    with allure.step("Attempt to create an admin with a non-complex password"):
        sp.create_admin(
            data.username, data.full_name, data.email, data.password,
            role=data.role, permissions=data.permissions,
        )
        sp.wait_for_load()

    with allure.step("Verify an error is shown and no account was created"):
        expect(sp.error_alert).to_be_visible()
        expect(sp.page_title).to_contain_text(f"({before})")


# ---------------------------------------------------------------------------
# TC-279  A never-logged-in admin shows 'Never' / blank Last IP
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-279")
@allure.story("Admin User Management")
@allure.title("TC-279: A newly created admin shows 'Never' last login and blank Last IP")
def test_tc279_new_admin_last_login_never(
    logged_in_admin_users_page: AdminUsersPage,
    throwaway_admin: AdminUserData,
):
    """
    Given a freshly created admin that has never logged in
    When  I find its row in the list
    Then  Last Login reads 'Never' (or a placeholder dash)
    And   Last IP is blank

    AIO: KAN-TC-279 | data: throwaway sub-admin (never logged in)
    """
    sp = logged_in_admin_users_page
    user = throwaway_admin

    with allure.step("Locate the newly created admin"):
        expect(sp.admin_row(user.username)).to_be_visible()

    with allure.step("Verify Last Login reads 'Never' / placeholder"):
        expect(sp.last_login_cell(user.username)).to_have_text(
            re.compile(r"Never|—|–|-|N/?A", re.IGNORECASE)
        )

    with allure.step("Verify Last IP is blank"):
        last_ip = sp.last_ip_cell(user.username).text_content().strip()
        assert last_ip in ("", "—", "–", "-"), (
            f"Last IP is not blank for a never-logged-in admin: {last_ip!r}"
        )
