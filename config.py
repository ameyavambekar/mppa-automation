"""Central URL configuration for the MPPA portal.

Every portal URL derives from a single source of truth — ``MPPA_BASE_URL`` in
the ``.env`` file — so switching environments (e.g. dev ↔ prod) is a one-line
change. Page objects import the area base they need from here instead of
hard-coding hosts or reading their own environment variables.
"""
import os

from dotenv import load_dotenv

load_dotenv()

# Single source of truth, read from .env. Points at the agency auth area, e.g.
# https://mppa.sppuef.in/module/agency/auth
BASE_URL = os.getenv(
    "MPPA_BASE_URL", "https://mppa.sppuef.in/module/agency/auth"
).rstrip("/")

# Common module root shared by every area, e.g. https://mppa.sppuef.in/module
MODULE_ROOT = BASE_URL.rsplit("/agency/auth", 1)[0]

# Area bases derived from the single root above.
AUTH_BASE   = BASE_URL                       # .../module/agency/auth
AGENCY_BASE = f"{MODULE_ROOT}/agency"        # .../module/agency
FORMS_BASE  = f"{MODULE_ROOT}/agency/forms"  # .../module/agency/forms
ADMIN_BASE  = f"{MODULE_ROOT}/admin"         # .../module/admin
NOTICES_URL = f"{MODULE_ROOT}/notices.php"   # .../module/notices.php (agency board)

# Common endpoints derived from the area bases.
ADMIN_LOGOUT_URL = f"{ADMIN_BASE}/auth/logout.php"  # admin logout
