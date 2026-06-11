import allure

from pages.base_page import BasePage


class AdminUsersPage(BasePage):
    """Super Admin — Admin User Management dashboard.

    Lists all admin accounts in a table with an active/inactive toggle and
    per-row Perms / Delete actions, plus two modals: Create Admin
    (``#create-modal``) and Permissions (``#perm-modal``). Row locators are
    keyed by username since row order and numeric admin IDs vary.

    Deleting an admin fires a JS ``confirm()`` dialog — handled via the
    base-page dialog pattern. Toggle failures surface as JS ``alert()``s.
    """

    # Permission checkbox values available in both modals
    PERMISSIONS = (
        "view_agencies", "edit_agency_status", "view_part_a", "view_part_b",
        "view_part_c", "view_part_e", "view_part_f", "view_enclosures",
        "view_declarations", "manage_appeals", "view_audit_log",
        "view_sessions", "manage_admins", "view_payments",
    )

    # ── Topbar ────────────────────────────────────────────────────────────────

    @property
    def topbar_role_badge(self):
        # e.g. "👑 Super Admin"
        return self.page.locator("#adm-topbar .tb-badge")

    @property
    def topbar_title(self):
        return self.page.locator("#adm-topbar h1")

    @property
    def topbar_welcome_text(self):
        return self.page.locator("#adm-topbar .tb-user")

    @property
    def topbar_logout_link(self):
        return self.page.locator("#adm-topbar a[href*='logout']")

    # ── Sidebar ───────────────────────────────────────────────────────────────

    @property
    def sidebar_user_name(self):
        return self.page.locator("#adm-sb .sb-user .nm")

    @property
    def sidebar_user_role(self):
        return self.page.locator("#adm-sb .sb-user .rl")

    def sidebar_nav_item(self, label: str):
        """label as shown in the sidebar, e.g. 'Admin Users', 'Audit Log',
        'Agencies', 'Permissions'."""
        return self.page.locator(f"//div[@id='adm-sb']//a[contains(normalize-space(.),'{label}')]")

    @property
    def sidebar_active_item(self):
        return self.page.locator("#adm-sb .ni.active")

    def sidebar_nav_badge(self, label: str):
        """The count badge on a sidebar item, e.g. '4' on 'Admin Users'."""
        return self.sidebar_nav_item(label).locator(".bc")

    # ── Page header ───────────────────────────────────────────────────────────

    @property
    def page_title(self):
        # "👤 Admin User Management (4)"
        return self.page.locator(".adm-page-title span").first

    @property
    def total_accounts_text(self):
        # "4 total admin accounts"
        return self.page.locator("//p[contains(text(),'total admin accounts')]")

    @property
    def create_admin_button(self):
        return self.page.locator("//button[contains(normalize-space(.),'Create Admin')]").first

    # ── Alerts ────────────────────────────────────────────────────────────────

    @property
    def success_alert(self):
        return self.page.locator(".salt-s")

    @property
    def error_alert(self):
        return self.page.locator(".salt-e")

    # ── Admin users table (rows keyed by username) ────────────────────────────

    @property
    def admin_table(self):
        return self.page.locator(".stbl")

    @property
    def admin_rows(self):
        return self.page.locator(".stbl tbody tr")

    def admin_row(self, username: str):
        return self.page.locator(f"//table[contains(@class,'stbl')]//tbody/tr[td[normalize-space(text())='{username}']]")

    def full_name_cell(self, username: str):
        return self.admin_row(username).locator("td").nth(2)

    def email_cell(self, username: str):
        return self.admin_row(username).locator("td").nth(3)

    def role_badge(self, username: str):
        # Carries class sb-superadmin / sb-admin / sb-officer / sb-viewer
        return self.admin_row(username).locator(".sb")

    def active_toggle(self, username: str):
        return self.admin_row(username).locator(".stog input[type='checkbox']")

    def active_status_label(self, username: str):
        # "Active" / "Inactive" text next to the toggle (span id='stl-{admin_id}')
        return self.admin_row(username).locator("span[id^='stl-']")

    def last_login_cell(self, username: str):
        return self.admin_row(username).locator("td").nth(6)

    def last_ip_cell(self, username: str):
        return self.admin_row(username).locator("td").nth(7)

    def permissions_button(self, username: str):
        return self.admin_row(username).locator("//button[contains(normalize-space(.),'Perms')]")

    def delete_button(self, username: str):
        return self.admin_row(username).locator("form button[type='submit']")

    def protected_label(self, username: str):
        # Shown instead of action buttons for the superadmin account
        return self.admin_row(username).locator("//span[contains(text(),'Protected')]")

    # ── Create Admin modal (#create-modal) ────────────────────────────────────

    @property
    def create_modal(self):
        return self.page.locator("#create-modal")

    @property
    def create_username_input(self):
        return self.create_modal.locator("input[name='username']")

    @property
    def create_full_name_input(self):
        return self.create_modal.locator("input[name='full_name']")

    @property
    def create_email_input(self):
        return self.create_modal.locator("input[name='email']")

    @property
    def create_password_input(self):
        return self.create_modal.locator("input[name='password']")

    @property
    def create_role_select(self):
        return self.create_modal.locator("select[name='role']")

    def create_permission_checkbox(self, permission: str):
        """permission: one of PERMISSIONS, e.g. 'view_agencies'."""
        return self.create_modal.locator(f"input[name='permissions[]'][value='{permission}']")

    @property
    def create_submit_button(self):
        return self.create_modal.locator("button[type='submit']")

    @property
    def create_cancel_button(self):
        return self.create_modal.locator("//button[normalize-space(text())='Cancel']")

    @property
    def create_close_button(self):
        return self.create_modal.locator("//button[normalize-space(text())='✕']")

    # ── Permissions modal (#perm-modal) ───────────────────────────────────────

    @property
    def perm_modal(self):
        return self.page.locator("#perm-modal")

    @property
    def perm_modal_admin_name(self):
        return self.page.locator("#perm-name")

    def perm_checkbox(self, permission: str):
        """permission: one of PERMISSIONS, e.g. 'manage_appeals'."""
        return self.perm_modal.locator(f".perm-cb[value='{permission}']")

    @property
    def perm_checkboxes(self):
        return self.perm_modal.locator(".perm-cb")

    @property
    def perm_select_all_button(self):
        return self.perm_modal.locator("//button[normalize-space(text())='Select All']")

    @property
    def perm_clear_all_button(self):
        return self.perm_modal.locator("//button[normalize-space(text())='Clear All']")

    @property
    def perm_save_button(self):
        return self.perm_modal.locator("button[type='submit']")

    @property
    def perm_cancel_button(self):
        return self.perm_modal.locator("//button[normalize-space(text())='Cancel']")

    @property
    def perm_close_button(self):
        return self.perm_modal.locator("//button[normalize-space(text())='✕']")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Admin Users management page directly")
    def open(self):
        import os
        base = os.getenv("MPPA_ADMIN_BASE_URL", "https://devmppa.sppuef.in/module/admin")
        self.navigate(f"{base}/admins/index.php")

    @allure.step("Click sidebar item: {label}")
    def click_sidebar_item(self, label: str):
        self.sidebar_nav_item(label).click()

    @allure.step("Click topbar Logout")
    def click_logout(self):
        self.topbar_logout_link.click()

    # -- Table actions --

    @allure.step("Toggle active state for admin: {username}")
    def toggle_admin_active(self, username: str):
        """Clicks the toggle track (the checkbox itself is visually hidden)."""
        self.admin_row(username).locator(".stog-track").click()

    @allure.step("Delete admin '{username}' (confirm dialog: {action})")
    def delete_admin(self, username: str, action: str = "accept") -> str:
        """Clicks the row's delete button and answers the 'Delete this admin?'
        confirm dialog. action='accept' confirms, 'dismiss' cancels.
        Returns the dialog message."""
        return self.click_and_handle_alert(self.delete_button(username), action=action)

    # -- Create Admin modal actions --

    @allure.step("Open the Create Admin modal")
    def open_create_admin_modal(self):
        self.create_admin_button.click()

    @allure.step("Select role in Create Admin modal: {role}")
    def select_create_role(self, role: str):
        """role: 'officer', 'admin' or 'viewer'."""
        self.create_role_select.select_option(value=role)

    @allure.step("Set permission '{permission}' to {checked} in Create Admin modal")
    def set_create_permission(self, permission: str, checked: bool = True):
        self.create_permission_checkbox(permission).set_checked(checked)

    @allure.step("Submit the Create Admin modal")
    def submit_create_admin(self):
        self.create_submit_button.click()

    @allure.step("Cancel the Create Admin modal")
    def cancel_create_admin(self):
        self.create_cancel_button.click()

    @allure.step("Create admin user: {username} (role: {role})")
    def create_admin(self, username: str, full_name: str, email: str, password: str,
                     role: str = "officer", permissions: list = None):
        """Opens the Create Admin modal, fills all fields, ticks the given
        permissions (values from PERMISSIONS) and submits."""
        self.open_create_admin_modal()
        self.create_username_input.fill(username)
        self.create_full_name_input.fill(full_name)
        self.create_email_input.fill(email)
        self.create_password_input.fill(password)
        self.select_create_role(role)
        for permission in (permissions or []):
            self.set_create_permission(permission, True)
        self.submit_create_admin()

    # -- Permissions modal actions --

    @allure.step("Open the Permissions modal for admin: {username}")
    def open_permissions_modal(self, username: str):
        self.permissions_button(username).click()

    @allure.step("Set permission '{permission}' to {checked} in Permissions modal")
    def set_permission(self, permission: str, checked: bool = True):
        self.perm_checkbox(permission).set_checked(checked)

    @allure.step("Click 'Select All' permissions")
    def select_all_permissions(self):
        self.perm_select_all_button.click()

    @allure.step("Click 'Clear All' permissions")
    def clear_all_permissions(self):
        self.perm_clear_all_button.click()

    @allure.step("Save the Permissions modal")
    def save_permissions(self):
        self.perm_save_button.click()

    @allure.step("Cancel the Permissions modal")
    def cancel_permissions(self):
        self.perm_cancel_button.click()

    @allure.step("Update permissions for admin '{username}'")
    def update_permissions(self, username: str, permissions: list):
        """Opens the Permissions modal for username, clears everything, ticks
        exactly the given permissions and saves."""
        self.open_permissions_modal(username)
        self.clear_all_permissions()
        for permission in permissions:
            self.set_permission(permission, True)
        self.save_permissions()

    def get_checked_permissions(self) -> list:
        """Returns the permission values currently ticked in the open
        Permissions modal."""
        checked = []
        for i in range(self.perm_checkboxes.count()):
            checkbox = self.perm_checkboxes.nth(i)
            if checkbox.is_checked():
                checked.append(checkbox.get_attribute("value"))
        return checked
