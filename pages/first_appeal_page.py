import allure

from pages.base_page import BasePage
from config import AGENCY_BASE


class FirstAppealPage(BasePage):
    """Agency — Application for First Appeal, FORM-III (/module/agency/appeals/first.php).

    The form an agency files to appeal a Registering Authority order under
    Section 7(1) of the MPPA (Regulation) Act, 2025 (See Rule 8). It posts back
    to itself as ``multipart/form-data`` (file uploads) and is laid out in the
    numbered sections seen on screen:

    * 5  — Details of Order Appealed Against (order number / date / authority)
    * 6  — Grounds of Appeal (``grounds[]`` checkboxes; 'Other' reveals a text box)
    * 7  — Brief Facts (``brief_facts`` textarea)
    * 8  — Relief Sought (``relief_type`` radios + ``relief_sought`` textarea)
    * 9  — Limitation (``comm_date`` + ``within_time`` radios; 'No' reveals the
           ``delay_reason`` box for condonation)
    * 10 — Index of Documents (five optional file inputs, accept pdf/jpg/png)
    * Verification & Declaration (place / signatory / required declaration tick)

    A reference strip at the top is auto-filled from the logged-in agency
    (Agency Name, Registration No., Address, Email, Mobile). When the agency
    already has a first appeal on file the page renders the ``.existing-notice``
    banner instead of an empty form.

    Locators are ``@property`` methods, actions are ``@allure.step`` decorated,
    and all assertions stay in the tests (use ``expect()`` against these
    locators).
    """

    # grounds[] checkbox values (Section 6)
    GROUNDS = (
        "error_of_law", "procedural_irregularity", "jurisdictional_error",
        "non_consideration", "natural_justice", "other",
    )
    # relief_type radio values (Section 8)
    RELIEFS = (
        "Setting Aside the Order",
        "Modification of Order",
        "Remand for Fresh Consideration",
    )
    # logical document slot → file input name (Section 10)
    DOC_SLOTS = {
        "original": "doc_original",   # (a) Photocopy of Original Application
        "ack":      "doc_ack",        # (b) Acknowledgement issued by Registering Authority
        "fees":     "doc_fees",       # (c) Fee Receipt
        "order":    "doc_order",      # (d) Order of Registering Authority (marked Required)
        "other":    "doc_other",      # (e) Any Other Documents
    }

    # ── Page header & reference strip ─────────────────────────────────────────

    @property
    def form_badge(self):
        # "FORM-III" pill next to the page title
        return self.page.locator("//span[normalize-space(text())='FORM-III']")

    @property
    def page_heading(self):
        return self.page.locator("//h2[normalize-space(text())='Application for First Appeal']")

    @property
    def my_application_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'My Application')]")

    @property
    def second_appeal_link(self):
        return self.page.locator("//a[contains(normalize-space(.),'Second Appeal')]")

    def ref_item(self, label: str):
        """A reference-strip value cell by its label, e.g. 'Agency Name',
        'Registration No.', 'Reg. Address', 'Email', 'Mobile'."""
        return self.page.locator(
            f"//div[@class='form-ref-item'][div[@class='label' and "
            f"normalize-space(text())='{label}']]/div[@class='value']"
        )

    @property
    def existing_appeal_notice(self):
        """Amber banner shown when the agency already has a first appeal filed."""
        return self.page.locator(".existing-notice")

    # ── Messages ──────────────────────────────────────────────────────────────

    @property
    def success_alert(self):
        return self.page.locator(".alert-success")

    @property
    def error_alert(self):
        return self.page.locator(".alert-error")

    @property
    def info_alert(self):
        return self.page.locator(".alert-info")

    # ── Section 5 — Details of Order Appealed Against ─────────────────────────

    @property
    def order_number_input(self):
        return self.page.locator("input[name='order_number']")

    @property
    def order_date_input(self):
        return self.page.locator("input[name='order_date']")

    @property
    def order_authority_input(self):
        return self.page.locator("input[name='order_authority']")

    # ── Section 6 — Grounds of Appeal ─────────────────────────────────────────

    def ground_checkbox(self, value: str):
        """A grounds-of-appeal checkbox by its value (one of GROUNDS)."""
        return self.page.locator(f"input[name='grounds[]'][value='{value}']")

    @property
    def grounds_other_input(self):
        # Revealed when the 'Other' ground is ticked
        return self.page.locator("input[name='grounds_other']")

    @property
    def other_specify_box(self):
        return self.page.locator("#other_specify")

    # ── Section 7 — Brief Facts ───────────────────────────────────────────────

    @property
    def brief_facts_textarea(self):
        return self.page.locator("textarea[name='brief_facts']")

    # ── Section 8 — Relief Sought ─────────────────────────────────────────────

    def relief_radio(self, value: str):
        """A relief-type radio by its value (one of RELIEFS)."""
        return self.page.locator(f"input[name='relief_type'][value='{value}']")

    @property
    def relief_sought_textarea(self):
        return self.page.locator("textarea[name='relief_sought']")

    # ── Section 9 — Limitation ────────────────────────────────────────────────

    @property
    def communication_date_input(self):
        return self.page.locator("input[name='comm_date']")

    def within_time_radio(self, value: str):
        """The 'Appeal Filed Within Prescribed Time' radio — value 'yes' or 'no'."""
        return self.page.locator(f"input[name='within_time'][value='{value}']")

    @property
    def delay_box(self):
        return self.page.locator("#delay_box")

    @property
    def delay_reason_textarea(self):
        return self.page.locator("textarea[name='delay_reason']")

    # ── Section 10 — Index of Documents ───────────────────────────────────────

    def document_input(self, slot: str):
        """A file input by logical slot (one of DOC_SLOTS keys)."""
        return self.page.locator(f"input[name='{self.DOC_SLOTS[slot]}']")

    # ── Verification & Declaration ────────────────────────────────────────────

    @property
    def place_input(self):
        return self.page.locator("input[name='place']")

    @property
    def signatory_name_input(self):
        return self.page.locator("input[name='signatory_name']")

    @property
    def signatory_designation_input(self):
        return self.page.locator("input[name='signatory_designation']")

    @property
    def declaration_checkbox(self):
        # The only required checkbox on the form (grounds checkboxes are optional)
        return self.page.locator("input[type='checkbox'][required]")

    @property
    def submit_button(self):
        return self.page.locator("//button[@type='submit'][contains(., 'Submit First Appeal')]")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the First Appeal (FORM-III) form")
    def open(self):
        self.navigate(f"{AGENCY_BASE}/appeals/first.php")

    @allure.step("Fill order details: number={order_number}, date={order_date}")
    def fill_order_details(self, order_number: str, order_date: str, order_authority: str):
        """``order_date`` in yyyy-mm-dd format for the native date input."""
        self.order_number_input.fill(order_number)
        self.order_date_input.fill(order_date)
        self.order_authority_input.fill(order_authority)

    @allure.step("Select grounds of appeal: {grounds}")
    def select_grounds(self, grounds):
        """grounds: an iterable of GROUNDS values to tick."""
        for value in grounds:
            self.ground_checkbox(value).check()

    @allure.step("Specify the 'Other' ground: {text}")
    def specify_other_ground(self, text: str):
        """Ticks 'Other' (if not already) and fills the revealed text box."""
        self.ground_checkbox("other").check()
        self.grounds_other_input.fill(text)

    @allure.step("Fill brief facts")
    def fill_brief_facts(self, text: str):
        self.brief_facts_textarea.fill(text)

    @allure.step("Select relief type: {relief_type}")
    def select_relief_type(self, relief_type: str):
        """relief_type: one of RELIEFS."""
        self.relief_radio(relief_type).check()

    @allure.step("Fill specific relief sought")
    def fill_relief_sought(self, text: str):
        self.relief_sought_textarea.fill(text)

    @allure.step("Fill date of communication of impugned order: {date}")
    def fill_communication_date(self, date: str):
        """``date`` in yyyy-mm-dd format."""
        self.communication_date_input.fill(date)

    @allure.step("Set 'filed within prescribed time' = {value}")
    def set_within_time(self, value: str):
        """value: 'yes' or 'no'. Selecting 'no' reveals the delay-reason box."""
        self.within_time_radio(value).check()

    @allure.step("Fill reasons for delay & prayer for condonation")
    def fill_delay_reason(self, text: str):
        self.delay_reason_textarea.fill(text)

    @allure.step("Upload document in slot '{slot}': {path}")
    def upload_document(self, slot: str, path: str):
        """slot: one of DOC_SLOTS keys."""
        self.document_input(slot).set_input_files(path)

    @allure.step("Upload supporting documents")
    def upload_documents(self, documents: dict):
        """documents: mapping of DOC_SLOTS key → file path."""
        for slot, path in documents.items():
            self.upload_document(slot, path)

    @allure.step("Fill verification: place={place}, signatory={signatory_name}")
    def fill_verification(self, place: str, signatory_name: str, signatory_designation: str):
        self.place_input.fill(place)
        self.signatory_name_input.fill(signatory_name)
        self.signatory_designation_input.fill(signatory_designation)

    @allure.step("Tick the declaration checkbox")
    def accept_declaration(self):
        self.declaration_checkbox.check()

    @allure.step("Click 'Submit First Appeal (FORM-III)'")
    def submit(self):
        self.submit_button.click()
        self.wait_for_load()

    @allure.step("Click 'Submit First Appeal' and handle any alert dialog")
    def submit_and_handle_alert(self, action: str = "accept") -> str:
        """Submits and returns the alert message (for blocked / confirm flows)."""
        return self.click_and_handle_alert(self.submit_button, action=action)

    # ── Composite actions ─────────────────────────────────────────────────────

    @allure.step("Fill the entire First Appeal form from: {data.scenario_label}")
    def fill_appeal(self, data):
        """Fills every section from a ``FirstAppealData`` value object — but does
        not submit. Conditional sections (Other ground, delay reason) are filled
        only when the data calls for them."""
        self.fill_order_details(data.order_number, data.order_date, data.order_authority)
        self.select_grounds(data.grounds)
        if "other" in data.grounds and data.grounds_other:
            self.specify_other_ground(data.grounds_other)
        self.fill_brief_facts(data.brief_facts)
        if data.relief_type:
            self.select_relief_type(data.relief_type)
        self.fill_relief_sought(data.relief_sought)
        self.fill_communication_date(data.comm_date)
        self.set_within_time(data.within_time)
        if data.within_time == "no" and data.delay_reason:
            self.fill_delay_reason(data.delay_reason)
        if data.documents:
            self.upload_documents(data.documents)
        self.fill_verification(data.place, data.signatory_name, data.signatory_designation)
        self.accept_declaration()

    @allure.step("File the First Appeal end-to-end from: {data.scenario_label}")
    def file_appeal(self, data):
        """Fills the whole form and submits it."""
        self.fill_appeal(data)
        self.submit()

    # ── Read helpers (queries, not assertions) ────────────────────────────────

    def get_agency_name(self) -> str:
        return self.ref_item("Agency Name").text_content().strip()

    def get_registration_no(self) -> str:
        return self.ref_item("Registration No.").text_content().strip()

    def has_existing_appeal(self) -> bool:
        """Whether the page is showing the 'appeal already on file' banner."""
        return self.existing_appeal_notice.count() > 0
