"""
Fixtures — Form-II certificates (KAN-28)
========================================
The Super Admin reads every approved agency's certificate from Approved agencies → "📜 Cert" (the working admin
copy). ``approved_certificates`` lists those links once per test; ``open_admin_certificate`` opens one in a new
tab on the same session and closes it on teardown. The Licences & certificates "View Cert" link returns 404
(defect "Super admin" #59), so these fixtures do not use it.
"""

import pytest

from fixtures.drafts_fixtures import _admin_login, _admin_logout
from pages.admin.approved_agencies_page import AdminApprovedAgenciesPage
from pages.admin.certificate_view_page import AdminCertificatePage


@pytest.fixture
def approved_certificates(page) -> list[dict]:
    """The Super Admin's approved agencies with their certificate links (``{agency, href}``); logs out on teardown."""
    _admin_login(page)
    approved = AdminApprovedAgenciesPage(page)
    approved.open()
    yield approved.certificate_links()
    _admin_logout(page)


@pytest.fixture
def open_admin_certificate(page):
    """``open(href) -> AdminCertificatePage``: the admin copy of a certificate in a new tab on the Super Admin's
    session. Every tab opened is closed on teardown."""
    tabs = []

    def open_(href: str) -> AdminCertificatePage:
        tab = page.context.new_page()
        tabs.append(tab)
        tab.goto(href, wait_until="domcontentloaded")
        return AdminCertificatePage(tab)

    yield open_
    for tab in tabs:
        try:
            tab.close()
        except Exception:
            pass
