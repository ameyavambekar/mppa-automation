"""
Builds agency users on demand, up to a given Form-I stage.

The step tests only use an agency that has saved the previous step and never
the step under test (see fixtures/part*_fixtures.py), and every test that saves
uses its agency up. When a fixture runs out, it asks this builder for a new
one instead of skipping: the builder registers a brand-new agency through the
real registration form and saves each step up to ``stage`` with valid factory
data, recording every step in the state store as it goes.

    user = AgencyBuilder(page).build("part_c")       # Part A, B and C saved

Stages, in order: "registered", "part_a", "part_b", "part_c", "part_f",
"enclosures". A built agency's Part C has "Does the agency provide training?" = No,
its Part F has every certificate answered No, and "enclosures" uploads the six
mandatory documents (6/6).

The builder leaves the browser logged out; callers log in as the returned user.
"""

from __future__ import annotations

import allure
from playwright.sync_api import expect

from config import FORMS_BASE
from pages.enclosures_page import EnclosuresPage
from pages.login_page import LoginPage
from pages.partA_page import PART_A_LOCKED_STEP_URL, PartAPage
from pages.partB_page import PartBPage
from pages.partC_page import PartCPage
from pages.partF_page import PartFPage
from pages.registration_page import RegistrationPage
from test_data.agency_registration_factory import AgencyRegistrationFactory
from test_data.enclosures_factory import EnclosuresFactory
from test_data.partA_factory import PartAFactory
from test_data.partB_factory import PartBFactory
from test_data.partC_factory import PartCFactory
from test_data.partF_factory import PartFFactory
from utils.state_store import TestStateStore, UserRecord

STAGES = ("registered", "part_a", "part_b", "part_c", "part_f", "enclosures")
COMPANY = "Private Limited Company"
# The step whose tests use an agency built up to each stage — it must never have been saved.
NEXT_STEP = {"part_a": "part_b", "part_b": "part_c", "part_c": "part_f", "part_f": "enclosures",
             "enclosures": "premises"}


def available(stage: str, legal_constitution: str = COMPANY, store: TestStateStore = None) -> list[UserRecord]:
    """Agencies in the state store that have saved every step up to ``stage`` and never
    touched the next one — the pool the next step's tests draw from."""
    store = store or TestStateStore()
    steps = list(STAGES[1:STAGES.index(stage) + 1])
    users = store.get_agency_users_with_steps(steps, legal_constitution if stage == "part_a" else None)
    return [u for u in users if u.steps.get(NEXT_STEP[stage]) in (None, "not_started")]


class AgencyBuilder:

    def __init__(self, page, store: TestStateStore = None):
        self.page = page
        self.store = store or TestStateStore()

    @allure.step("Build a new agency up to '{stage}'")
    def build(self, stage: str, legal_constitution: str = COMPANY) -> UserRecord:
        """Registers a new agency and saves every step up to and including ``stage``.

        ``legal_constitution`` is the Part A agency type. Only a Private Limited
        Company can be built past Part A (the Part B data is for Directors)."""
        if stage not in STAGES:
            raise ValueError(f"Unknown stage '{stage}' — expected one of {STAGES}")
        if STAGES.index(stage) > STAGES.index("part_a") and legal_constitution != COMPANY:
            raise ValueError(f"Only a {COMPANY} can be built past Part A")
        user = self.register()
        steps = {"part_a": lambda u: self.save_part_a(u, legal_constitution),
                 "part_b": self.save_part_b, "part_c": self.save_part_c, "part_f": self.save_part_f,
                 "enclosures": self.upload_documents}
        if stage != "registered":
            self._login(user)
            for step in STAGES[1:STAGES.index(stage) + 1]:
                steps[step](user)
        self.page.context.clear_cookies()
        return self.store.get_user_by_username(user.username)

    # ── Registration ──────────────────────────────────────────────────────────

    @allure.step("Register a new agency")
    def register(self) -> UserRecord:
        """Submits the real registration form (random listed district) and records the user."""
        self.page.context.clear_cookies()
        data = AgencyRegistrationFactory.valid()
        registration = RegistrationPage(self.page)
        registration.open()
        registration.fill_agency_name(data.agency_name)
        registration.fill_credentials(data.username, data.password, data.confirm_password)
        expect(registration.username_helper).to_contain_text("Username available")
        registration.fill_contact_identity(data.email, data.pan_number, data.district, data.mobile, data.alt_phone)
        registration.fill_document_upload()
        registration.fill_captcha()
        registration.accept_declaration()
        with self.page.expect_response(
            lambda r: "register_process.php" in r.url and r.request.method == "POST"
            and b"check_" not in (r.request.post_data_buffer or b"")
        ) as response:
            registration.submit()
        body = response.value.json()
        if body.get("success") is not True:
            raise RuntimeError(f"Registration of {data.username} rejected: {body.get('message')}")
        self.store.record_user(
            role="agency", username=data.username, password=data.password, agency_name=data.agency_name,
            email=data.email, mobile=data.mobile, alt_phone=data.alt_phone, pan=data.pan_number,
            district=data.district, registration_id=body.get("registration_id") or body.get("application_id"),
        )
        self.page.context.clear_cookies()
        return self.store.get_user_by_username(data.username)

    def _login(self, user: UserRecord) -> None:
        login = LoginPage(self.page)
        login.open()
        login.login(user.username, user.password)
        self.page.wait_for_url(f"{FORMS_BASE}/**", timeout=15000)

    # ── Form-I steps ──────────────────────────────────────────────────────────

    @allure.step("Save Part A as '{legal_constitution}'")
    def save_part_a(self, user: UserRecord, legal_constitution: str = COMPANY) -> None:
        data = (PartAFactory.valid_mandatory_fields() if legal_constitution == COMPANY
                else PartAFactory.proprietorship_without_incorporation())
        data.legal_constitution = legal_constitution
        data = PartAFactory.for_user(data, user)
        part_a = PartAPage(self.page)
        part_a.open()
        self.page.wait_for_load_state("networkidle")
        part_a.select_legal_constitution(data.legal_constitution)
        part_a.fill_agency_date_of_establishment(data.date_of_establishment)
        if data.incorporation_no:
            part_a.fill_incorporation_no(data.incorporation_no)
        if data.incorporation_certificate:
            part_a.set_incorporation_certificate(data.incorporation_certificate)
        part_a.fill_tan(data.tan_number)
        part_a.set_tan_certificate(data.tan_certificate)
        part_a.fill_gst(data.gstin)
        part_a.set_gst_certificate(data.gst_certificate)
        part_a.fill_address_line1(data.address_line1)
        part_a.set_taluka(data.taluka)
        part_a.fill_city(data.city)
        part_a.fill_pincode(data.pincode)
        part_a.fill_authorised_signatory(data.authorised_signatory)
        part_a.fill_designation(data.designation)
        part_a.click_save_next()
        self.page.wait_for_load_state("networkidle")
        # Part A is saved once Part B opens instead of redirecting back to Part A.
        self.page.goto(f"{FORMS_BASE}/partB.php")
        expect(self.page).not_to_have_url(PART_A_LOCKED_STEP_URL)
        self.store.mark_form_step_status(username=user.username, step="part_a", status="completed",
                                         data=PartAFactory.state_store_data(data))

    @allure.step("Save Part B with one Director")
    def save_part_b(self, user: UserRecord) -> None:
        person = PartBFactory.valid_director()
        part_b = PartBPage(self.page)
        part_b.open()
        self.page.wait_for_load_state("networkidle")
        part_b.fill_key_person(0, person.full_name, person.aadhaar, person.mobile, person.address,
                               din=person.din, pan=person.pan)
        part_b.click_submit()
        # A successful save lands on Part C (partC.php?prev_saved=1).
        self.page.wait_for_url(f"{FORMS_BASE}/partC.php**", timeout=15000)
        self.store.mark_form_step_status(username=user.username, step="part_b", status="completed")

    @allure.step("Save Part C with the mandatory fields")
    def save_part_c(self, user: UserRecord) -> None:
        data = PartCFactory.minimal()
        part_c = PartCPage(self.page)
        part_c.open()
        self.page.wait_for_load_state("networkidle")
        part_c.fill_part_c_form(data.placement_type, data.service_mode, data.sectors, data.service_models,
                                data.charges_displayed)
        part_c.click_submit()
        expect(part_c.success_message).to_have_text(PartCPage.SAVED_MESSAGE)
        self.store.mark_form_step_status(username=user.username, step="part_c", status="completed")

    @allure.step("Save Part F with every certificate answered No")
    def save_part_f(self, user: UserRecord) -> None:
        part_f = PartFPage(self.page)
        part_f.open()
        self.page.wait_for_load_state("networkidle")
        part_f.select_place(PartFFactory.PLACE)
        part_f.click_submit()
        expect(part_f.success_message).to_have_text(PartFPage.SAVED_MESSAGE)
        self.store.mark_form_step_status(username=user.username, step="part_f", status="completed")

    @allure.step("Upload the six mandatory documents")
    def upload_documents(self, user: UserRecord) -> None:
        enclosures = EnclosuresPage(self.page)
        enclosures.open()
        self.page.wait_for_load_state("networkidle")
        enclosures.upload_documents(EnclosuresFactory.all_mandatory().documents)
        expect(enclosures.mandatory_counter).to_have_text(EnclosuresPage.counter_text(6))
        self.store.mark_form_step_status(username=user.username, step="enclosures", status="completed")
