import allure

from pages.admin.components.sidebar import AdminSidebar
from pages.base_page import BasePage
from config import ADMIN_BASE


class AdminPermissionsMatrixPage(BasePage):
    """Admin — Permissions Matrix (/module/admin/admins/permissions.php).

    A read-only grid showing every capability (rows) against every admin account
    (columns). Each cell holds one of three glyphs:

        ★  super admin — has all permissions (cannot be restricted)
        ✓  allowed
        ✕  denied

    The first column header is ``Permission``; every subsequent header is an
    admin's username with their role as a subtitle (e.g. ``super`` /
    ``superadmin``). The table carries no ids or classes on its cells, so rows
    are keyed by their permission label and admin columns are resolved by header
    position. There are no row actions here — permissions are edited from the
    Admin Users page, linked at the top and bottom of this view.
    """

    # The three cell glyphs and what they mean
    GLYPH_SUPER = "★"
    GLYPH_ALLOWED = "✓"
    GLYPH_DENIED = "✕"

    # Permission rows, in display order (labels without their leading emoji)
    PERMISSIONS = (
        "View Agencies", "Change Status", "Part A", "Part B", "Part C",
        "Part E", "Part F", "Enclosures", "Declarations", "Appeals",
        "Audit Log", "Sessions", "Manage Admins", "Payments",
    )

    # ── Reusable components ───────────────────────────────────────────────────

    @property
    def sidebar(self) -> AdminSidebar:
        """The shared left-nav sidebar component (#adm-sb)."""
        return AdminSidebar(self.page)

    # ── Page header ───────────────────────────────────────────────────────────

    @property
    def topbar_role_badge(self):
        # e.g. "👑 Super Admin"
        return self.page.locator("#adm-topbar .tb-badge")

    @property
    def page_title(self):
        # "🔒 Permissions Matrix"
        return self.page.locator(".adm-page-title span").first

    @property
    def legend(self):
        # "★ = Super Admin (all) · ✓ = allowed · ✕ = denied"
        return self.page.locator(".adm-page-title .pt-date")

    @property
    def admin_users_link(self):
        # "Admin Users →" intro link above the matrix
        return self.page.locator("//p[contains(., 'change permissions')]//a[contains(@href, 'index.php')]")

    # ── Matrix table ──────────────────────────────────────────────────────────

    @property
    def matrix_table(self):
        return self.page.locator(".scard table")

    @property
    def column_headers(self):
        """All header cells, including the leading 'Permission' column."""
        return self.matrix_table.locator("thead th")

    @property
    def admin_column_headers(self):
        """Admin columns only (the 'Permission' header excluded)."""
        return self.matrix_table.locator("thead th:not(:first-child)")

    def admin_column_header(self, username: str):
        """The header cell for an admin, matched by username (the first text
        line of the header, above the role subtitle)."""
        return self.matrix_table.locator(
            f"//thead//th[normalize-space(text())='{username}']"
        )

    def admin_role_subtitle(self, username: str):
        """The role label shown beneath an admin's username, e.g. 'superadmin',
        'admin', 'viewer'."""
        return self.admin_column_header(username).locator("span")

    @property
    def permission_rows(self):
        return self.matrix_table.locator("tbody tr")

    def permission_row(self, permission: str):
        """A matrix row, keyed by its permission label (emoji ignored)."""
        return self.matrix_table.locator(
            f"//tbody/tr[td[1][contains(normalize-space(.), '{permission}')]]"
        )

    def permission_label_cell(self, permission: str):
        return self.permission_row(permission).locator("td").first

    def permission_cell(self, permission: str, username: str):
        """The cell at the intersection of a permission row and an admin column.
        The admin column index is resolved from the header positions."""
        return self.permission_row(permission).locator("td").nth(
            self._column_index(username)
        )

    def permission_glyph(self, permission: str, username: str):
        """The glyph span (★ / ✓ / ✕) inside an intersection cell."""
        return self.permission_cell(permission, username).locator("span")

    # ── Footer info box ───────────────────────────────────────────────────────

    @property
    def how_to_update_box(self):
        # "ℹ️ How to update permissions" explainer banner
        return self.page.locator("//div[.//p[contains(., 'How to update permissions')]]")

    @property
    def how_to_update_link(self):
        # "Admin Users" link inside the explainer banner
        return self.how_to_update_box.locator("//a[contains(@href, 'index.php')]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Permissions Matrix directly")
    def open(self):
        self.navigate(f"{ADMIN_BASE}/admins/permissions.php")

    @allure.step("Go to Admin Users from the intro link")
    def go_to_admin_users(self):
        self.admin_users_link.click()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def _column_index(self, username: str) -> int:
        """0-based td/th index of an admin's column (matches because each row
        has exactly as many cells as the header)."""
        headers = self.column_headers
        for i in range(headers.count()):
            first_line = headers.nth(i).inner_text().strip().splitlines()[0].strip()
            if first_line == username:
                return i
        raise ValueError(f"No admin column found for username {username!r}")

    def get_admin_usernames(self) -> list:
        """Usernames of every admin column, left to right."""
        headers = self.admin_column_headers
        return [
            headers.nth(i).inner_text().strip().splitlines()[0].strip()
            for i in range(headers.count())
        ]

    def get_permission_labels(self) -> list:
        """Permission row labels (with leading emoji stripped)."""
        rows = self.permission_rows
        labels = []
        for i in range(rows.count()):
            text = rows.nth(i).locator("td").first.inner_text().strip()
            # Drop a leading emoji/symbol token if present
            parts = text.split(None, 1)
            labels.append(parts[1] if len(parts) == 2 and not parts[0].isalnum() else text)
        return labels

    def get_role_for_admin(self, username: str) -> str:
        return self.admin_role_subtitle(username).inner_text().strip()

    def get_permission_glyph(self, permission: str, username: str) -> str:
        """The raw glyph (★ / ✓ / ✕) for a permission/admin pair."""
        return self.permission_glyph(permission, username).inner_text().strip()

    def get_permission_state(self, permission: str, username: str) -> str:
        """The glyph mapped to a state: 'all' (★), 'allowed' (✓) or
        'denied' (✕)."""
        glyph = self.get_permission_glyph(permission, username)
        return {
            self.GLYPH_SUPER: "all",
            self.GLYPH_ALLOWED: "allowed",
            self.GLYPH_DENIED: "denied",
        }.get(glyph, glyph)

    def has_permission(self, permission: str, username: str) -> bool:
        """True when the admin is granted the permission (super ★ or allowed ✓),
        False when denied (✕)."""
        return self.get_permission_state(permission, username) in ("all", "allowed")
