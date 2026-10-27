from datetime import datetime

import allure

from config import FORMS_BASE
from pages.base_page import BasePage

PART_A_URL = f"{FORMS_BASE}/partA.php"
# Where any later wizard step redirects while Part A is unsaved (no on-page message).
PART_A_LOCKED_STEP_URL = f"{PART_A_URL}?error=complete_partA_first"


class PartAPage(BasePage):
    """Page object for Step 1 — Part A: Agency Basic Details (forms/partA.php).

    Sections: Agency Constitution, Tax Registration, Registered Office Address
    (with a Primary Maharashtra Office block when the head office is outside
    Maharashtra), Branch Offices in Maharashtra, Authorised Signatory Details.
    The agency name is shown read-only from registration; there are no agency
    name, PAN, e-mail, mobile, website or office-photo fields on this step.
    No beforeunload prompt is registered, so leaving the page never asks to confirm.
    """

    LEGAL_CONSTITUTIONS = (
        "Proprietorship", "Partnership Firm", "Private Limited Company", "Public Limited Company",
        "Limited Liability Partnership (LLP)", "Trust", "Society", "Section 8 Company", "Other",
    )
    PREMISE_TYPES = (
        "Owned Office Space", "Rented Office Space", "Co-working Space", "Home Office",
        "Virtual Office", "Government Premises", "Other",
    )

    # Client-side messages (hints update as you type; the rest are native alert() dialogs)
    GSTIN_VALID_HINT = "✓ Valid GSTIN format"
    GSTIN_INVALID_HINT = "✗ Invalid GSTIN format"
    PIN_VALID_HINT = "✓ Valid Maharashtra pincode"
    PIN_INVALID_HINT = "✗ Not a valid Maharashtra pincode (400000–445999)"
    DATE_FORMAT_ALERT = "Date of Establishment must be in DD/MM/YYYY format."
    DATE_FUTURE_ALERT = "Date of Establishment cannot be in the future."
    FILE_TOO_LARGE_ALERT = "is larger than 2 MB. Please choose a smaller file."
    FILE_TOO_SMALL_ALERT = "is smaller than 10 KB. Please upload a clear, complete scan."
    MH_OFFICE_REQUIRED_TEXT = "At least one office in Maharashtra is mandatory for this registration."
    DISTRICT_FROM_REGISTRATION_HINT = "Selected at registration — it decides your Registering Authority"
    DISTRICT_OTHER_STATE_HINT = "District of the head office"
    PIN_RANGE_HINT = "Valid Maharashtra range: 400000–445999"
    PIN_OTHER_STATE_HINT = "6-digit PIN code"
    CERTIFICATE_ACCEPT = ".pdf,.jpg,.jpeg,.png"

    # ── Page headings & wizard chrome ─────────────────────────────────────────

    @property
    def title(self):
        """Heading 'Step 1 — Part A: Agency Basic Details'."""
        return self.page.locator("//h2[contains(text(),'Step 1')]")

    @property
    def agency_name_display(self):
        """Agency name shown read-only under the heading ('Agency: <name>')."""
        return self.page.locator("p.agency-sub strong")

    @property
    def deadline_banner(self):
        """Banner '<N> days left to complete all steps and pay — deadline …' shown
        above the wizard while the registration is unpaid."""
        return self.page.locator("//div[strong][text()[contains(.,'to complete all steps and pay')]]")

    @property
    def save_and_logout_link(self):
        """'Save & Log out' link inside the deadline banner (../auth/logout.php)."""
        return self.page.get_by_role("link", name="Save & Log out")

    def progress_step(self, label: str):
        """Progress-bar item for ``label`` ('Register', 'Part A', 'Part B', …, 'Payment').
        Items are not clickable; later steps are locked by redirect (PART_A_LOCKED_STEP_URL)."""
        return self.page.locator(f"//span[normalize-space()='{label}']/parent::div")

    def section_heading(self, name: str):
        """Section heading, e.g. 'Agency Constitution', 'Tax Registration',
        'Registered Office Address', 'Branch Offices in Maharashtra',
        'Authorised Signatory Details'."""
        return self.page.locator(f"//div[contains(@class,'pA-section')][normalize-space()='{name}']")

    # ── Agency Constitution ───────────────────────────────────────────────────

    @property
    def legal_constitution_select(self):
        """'Agency Type / Legal Constitution' (select[name='agency_type'], required)."""
        return self.page.locator("select[name='agency_type']")

    @property
    def date_of_establishment_input(self):
        """Read-only 'Date of Establishment' box (#doeText, DD/MM/YYYY), filled from the calendar."""
        return self.page.locator("#doeText")

    @property
    def date_calendar_button(self):
        """Calendar button next to the date box (#doeCalBtn)."""
        return self.page.locator("#doeCalBtn")

    @property
    def date_native_input(self):
        """Hidden native date picker behind the date box (#doeNative, max = today)."""
        return self.page.locator("#doeNative")

    @property
    def incorporation_no_input(self):
        """'Incorporation / Registration Certificate No.' (max 40; upper-cased, A-Z 0-9 / - . space).
        Not needed for a Proprietorship."""
        return self.page.locator("input[name='incorporation_no']")

    @property
    def incorporation_certificate_input(self):
        """'Incorporation / Registration Certificate' file input (PDF/JPG/PNG, 10 KB – 2 MB)."""
        return self.page.locator("input[name='incorporation_file']")

    @property
    def incorporation_no_required_mark(self):
        """'*' on the Incorporation No. label (#incReq) — hidden for a Proprietorship."""
        return self.page.locator("#incReq")

    @property
    def incorporation_certificate_required_mark(self):
        """'*' on the Incorporation Certificate label (#incFileReq) — hidden for a Proprietorship."""
        return self.page.locator("#incFileReq")

    # ── Tax Registration ──────────────────────────────────────────────────────

    @property
    def tan_number_input(self):
        """'TAN Number' (max 10; upper-cased, A-Z 0-9 only)."""
        return self.page.locator("input[name='tan_number']")

    @property
    def tan_certificate_input(self):
        """'TAN certificate / allotment letter' file input (PDF/JPG/PNG, 10 KB – 2 MB)."""
        return self.page.locator("input[name='tan_file']")

    @property
    def gst_number_input(self):
        """'GSTIN' (#gstinInput, max 15; upper-cased, A-Z 0-9 only)."""
        return self.page.locator("#gstinInput")

    @property
    def gstin_hint(self):
        """Live GSTIN hint under the field (#gstinHlp): 'n/15 characters', GSTIN_VALID_HINT or GSTIN_INVALID_HINT."""
        return self.page.locator("#gstinHlp")

    @property
    def gst_certificate_input(self):
        """'GST registration certificate' file input (PDF/JPG/PNG, 10 KB – 2 MB)."""
        return self.page.locator("input[name='gst_file']")

    # ── Registered Office Address ─────────────────────────────────────────────

    @property
    def head_office_state_select(self):
        """'State of the registered / head office' (#hoState, default Maharashtra)."""
        return self.page.locator("#hoState")

    @property
    def mh_office_section(self):
        """'Primary Maharashtra Office Location' block (#mhWarningBox) — shown (class 'show')
        and required only when the head office state is not Maharashtra."""
        return self.page.locator("#mhWarningBox")

    @property
    def mh_detect_location_button(self):
        """'Detect MH Office Location' button (#btnDetectMH)."""
        return self.page.locator("#btnDetectMH")

    @property
    def mh_address_line1_input(self):
        """Maharashtra office 'Address Line 1' (#mhAddr1, max 200)."""
        return self.page.locator("#mhAddr1")

    @property
    def mh_district_select(self):
        """Maharashtra office 'District' (#mhDistrict; values are district ids)."""
        return self.page.locator("#mhDistrict")

    @property
    def mh_taluka_select(self):
        """Maharashtra office 'Taluka' (#mhMandal; filled after a district is chosen)."""
        return self.page.locator("#mhMandal")

    @property
    def mh_city_input(self):
        """Maharashtra office 'City' (#mhCity, max 80)."""
        return self.page.locator("#mhCity")

    @property
    def mh_pincode_input(self):
        """Maharashtra office 'Pincode' (#mhPin, 6 digits, 400000–445999)."""
        return self.page.locator("#mhPin")

    @property
    def address_line1_input(self):
        """Head office 'Address Line 1' (#mainAddr1, required, max 200; address autocomplete)."""
        return self.page.locator("#mainAddr1")

    @property
    def address_line2_input(self):
        """Head office 'Address Line 2 (optional)' (max 200)."""
        return self.page.locator("input[name='address_line2']")

    @property
    def district_display(self):
        """Read-only head office 'District' (#hoDistrictMH) — the district chosen at
        registration, which decides the Registering Authority. Shown for Maharashtra."""
        return self.page.locator("#hoDistrictMH")

    @property
    def district_input(self):
        """Free-text head office 'District' (#hoDistrictOther) — shown when the state is not Maharashtra."""
        return self.page.locator("#hoDistrictOther")

    @property
    def district_hint(self):
        """Hint under the head office District (#hoDistrictHint): DISTRICT_FROM_REGISTRATION_HINT
        for Maharashtra, DISTRICT_OTHER_STATE_HINT otherwise."""
        return self.page.locator("#hoDistrictHint")

    @property
    def taluka_select(self):
        """Head office 'Taluka' drop-down (#mainTalukaSel) — shown for Maharashtra."""
        return self.page.locator("#mainTalukaSel")

    @property
    def taluka_input(self):
        """Free-text head office 'Taluka' (#mainTalukaTxt) — shown when the state is not Maharashtra."""
        return self.page.locator("#mainTalukaTxt")

    @property
    def city_input(self):
        """Head office 'City / Village' (#mainCity, required, max 80)."""
        return self.page.locator("#mainCity")

    @property
    def pincode_input(self):
        """Head office 'Pincode' (#mainPin, required, 6 digits; Maharashtra range checked live)."""
        return self.page.locator("#mainPin")

    @property
    def pincode_hint(self):
        """Live pincode hint (#pinHlpMain): range text, PIN_VALID_HINT or PIN_INVALID_HINT."""
        return self.page.locator("#pinHlpMain")

    @property
    def pincode_mh_tag(self):
        """'MH only' tag on the head office Pincode label (#pinMhTag) — hidden for other states."""
        return self.page.locator("#pinMhTag")

    # ── Branch Offices in Maharashtra ─────────────────────────────────────────

    @property
    def add_branch_button(self):
        """'Add Branch Office' button — appends a branch card."""
        return self.page.locator("button.btn-add-branch")

    @property
    def branch_cards(self):
        """All branch cards (.branch-card), in display order."""
        return self.page.locator(".branch-card")

    def branch_field(self, index: int, field: str):
        """Field of the ``index``-th branch card (0-based). ``field`` is one of
        address, district_id, mandal_taluka, city, pincode, office_premise_type,
        office_premise_other."""
        return self.branch_cards.nth(index).locator(f"[name$='[{field}]']")

    def branch_remove_button(self, index: int):
        """'✕ Remove' button of the ``index``-th branch card (0-based)."""
        return self.branch_cards.nth(index).locator("button.btn-remove")

    @property
    def branch_numbers(self):
        """Number badges of all branch cards (.branch-num) — renumbered after a removal.
        (The 'Branch Office N' title text is not renumbered by the page.)"""
        return self.page.locator(".branch-card .branch-num")

    # ── Authorised Signatory Details ──────────────────────────────────────────

    @property
    def authorised_signatory_input(self):
        """'Name of Authorised Signatory' (required, max 100)."""
        return self.page.locator("input[name='authorized_signatory']")

    @property
    def designation_input(self):
        """'Designation' (required, max 100)."""
        return self.page.locator("input[name='designation']")

    @property
    def aadhaar_input(self):
        """'Aadhaar Number (optional)' (12 digits, non-digits stripped)."""
        return self.page.locator("input[name='aadhaar_number']")

    # ── Submit & server feedback ──────────────────────────────────────────────

    @property
    def submit_button(self):
        """'Save Part A & Continue' submit button."""
        return self.page.locator("button.btn-save[type='submit']")

    @property
    def error_alert(self):
        """Server error banner shown after a rejected save (.pA-alert-error)."""
        return self.page.locator(".pA-alert-error, .alert-error")

    @property
    def success_alert(self):
        """Server success banner (.pA-alert-success)."""
        return self.page.locator(".pA-alert-success, .alert-success")

    @property
    def rejected_fields(self):
        """Fields the server rejected on the last save — marked with class 'is-bad'."""
        return self.page.locator(".is-bad")

    def rejected_field(self, name: str):
        """The field named ``name`` if the server rejected it on the last save (class 'is-bad')."""
        return self.page.locator(f"[name='{name}'].is-bad")

    # ── Actions ───────────────────────────────────────────────────────────────

    def open(self):
        """Navigates to Step 1 — Part A (requires a logged-in agency session)."""
        self.navigate(PART_A_URL)

    @allure.step("Click 'Save & Log out'")
    def save_and_logout(self):
        self.save_and_logout_link.click()

    @allure.step("Select Legal Constitution: {legal_constitution}")
    def select_legal_constitution(self, legal_constitution: str):
        self.legal_constitution_select.select_option(value=legal_constitution)

    @allure.step("Set Date of Establishment: {date}")
    def fill_agency_date_of_establishment(self, date: str):
        """Sets the Date of Establishment through the calendar. ``date`` is
        dd-mm-yyyy or dd/mm/yyyy. The visible box is read-only and is filled by the
        page from the native date picker, so the date is set on the picker and its
        change event fired (the box then shows DD/MM/YYYY)."""
        for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
            try:
                iso = datetime.strptime(date, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"Date of Establishment must be dd-mm-yyyy or dd/mm/yyyy, got {date!r}")
        self.date_native_input.evaluate(
            "(el, v) => { el.value = v; el.dispatchEvent(new Event('change', {bubbles: true})); }", iso
        )

    @allure.step("Force Date of Establishment text: {text}")
    def force_date_of_establishment_text(self, text: str):
        """Writes ``text`` straight into the read-only date box, bypassing the calendar
        (what a tester does with developer tools) — to exercise the submit-time
        DATE_FORMAT_ALERT / DATE_FUTURE_ALERT checks."""
        self.date_of_establishment_input.evaluate("(el, v) => { el.value = v; }", text)

    @allure.step("Fill Incorporation / Registration Certificate No.: {number}")
    def fill_incorporation_no(self, number: str):
        self.incorporation_no_input.fill(number)
        self.incorporation_no_input.blur()

    @allure.step("Set Incorporation Certificate: {path}")
    def set_incorporation_certificate(self, path: str):
        self.incorporation_certificate_input.set_input_files(path)

    @allure.step("Fill TAN: {tan}")
    def fill_tan(self, tan: str):
        self.tan_number_input.fill(tan)
        self.tan_number_input.blur()

    @allure.step("Set TAN Certificate: {path}")
    def set_tan_certificate(self, path: str):
        self.tan_certificate_input.set_input_files(path)

    @allure.step("Fill GSTIN: {gst}")
    def fill_gst(self, gst: str):
        self.gst_number_input.fill(gst)
        self.gst_number_input.blur()

    @allure.step("Set GST Certificate: {path}")
    def set_gst_certificate(self, path: str):
        self.gst_certificate_input.set_input_files(path)

    @allure.step("Choose file {path} and handle any alert")
    def set_file_and_handle_alert(self, file_input, path: str) -> str:
        """Sets ``path`` on ``file_input`` and returns the message of the pop-up the
        page shows for a file outside 10 KB – 2 MB ("" if none). The page clears
        the input after such a pop-up."""
        messages = []

        def handle_dialog(dialog):
            messages.append(dialog.message)
            dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        file_input.set_input_files(path)
        self.page.wait_for_timeout(300)  # the alert is raised from the input's change handler
        self.page.remove_listener("dialog", handle_dialog)
        return messages[0] if messages else ""

    @allure.step("Select head office State: {state}")
    def select_head_office_state(self, state: str):
        """Selecting anything but Maharashtra reveals the Primary Maharashtra Office block
        and switches District / Taluka to free-text inputs."""
        self.head_office_state_select.select_option(value=state)

    @allure.step("Fill Primary Maharashtra Office")
    def fill_mh_office(self, address: str, district: str, taluka: str, city: str, pincode: str):
        """Fills the Primary Maharashtra Office block (only shown for a head office outside
        Maharashtra). ``district`` is the district name; ``taluka`` must belong to it."""
        self.mh_address_line1_input.fill(address)
        self.mh_district_select.select_option(label=district)
        self.mh_taluka_select.select_option(value=taluka)
        self.mh_city_input.fill(city)
        self.mh_pincode_input.fill(pincode)
        self.mh_pincode_input.blur()

    @allure.step("Fill Address Line 1: {address1}")
    def fill_address_line1(self, address1: str):
        self.address_line1_input.fill(address1)
        self.address_line1_input.blur()

    @allure.step("Fill Address Line 2: {address2}")
    def fill_address_line2(self, address2: str):
        self.address_line2_input.fill(address2)
        self.address_line2_input.blur()

    @allure.step("Fill head office District: {district}")
    def fill_district(self, district: str):
        """Free-text district — only editable when the head office is outside Maharashtra."""
        self.district_input.fill(district)
        self.district_input.blur()

    @allure.step("Set head office Taluka: {taluka}")
    def set_taluka(self, taluka: str):
        """Picks ``taluka`` from the drop-down (Maharashtra) or types it (other states)."""
        if self.taluka_select.is_visible():
            self.taluka_select.select_option(value=taluka)
        else:
            self.taluka_input.fill(taluka)
            self.taluka_input.blur()

    @allure.step("Fill City / Village: {city}")
    def fill_city(self, city: str):
        self.city_input.fill(city)
        self.city_input.blur()

    @allure.step("Fill Pincode: {pincode}")
    def fill_pincode(self, pincode: str):
        self.pincode_input.fill(pincode)
        self.pincode_input.blur()

    @allure.step("Select Maharashtra office District: {district}")
    def select_mh_district(self, district: str):
        """Selects the Primary Maharashtra Office district by name; its Taluka list then loads."""
        self.mh_district_select.select_option(label=district)

    @allure.step("Click 'Add Branch Office'")
    def click_add_branch(self):
        """Appends an empty branch card."""
        self.add_branch_button.click()

    @allure.step("Set branch #{index} {field}: {value}")
    def fill_branch_field(self, index: int, field: str, value: str):
        """Types ``value`` into a text field of the ``index``-th branch card (0-based)."""
        self.branch_field(index, field).fill(value)
        self.branch_field(index, field).blur()

    @allure.step("Select branch #{index} Office Premise Type: {premise_type}")
    def select_branch_premise(self, index: int, premise_type: str):
        """'Other' reveals the branch's mandatory 'Please Specify' field."""
        self.branch_field(index, "office_premise_type").select_option(value=premise_type)

    @allure.step("Type into {field}: {text}")
    def type_into(self, field: str, text: str):
        """Types ``text`` into the text field exposed as property ``field`` (e.g. 'tan_number_input')
        and blurs it, so the page's as-you-type rules run."""
        locator = getattr(self, field)
        locator.fill(text)
        locator.blur()

    @allure.step("Add Branch Office: {city}")
    def add_branch(self, address: str, district: str, taluka: str, city: str, pincode: str,
                   premise_type: str, premise_other: str = None):
        """Clicks 'Add Branch Office' and fills the new card. ``district`` is the district
        name; ``premise_other`` is required when ``premise_type`` is 'Other'."""
        self.add_branch_button.click()
        i = self.branch_cards.count() - 1
        self.branch_field(i, "address").fill(address)
        self.branch_field(i, "district_id").select_option(label=district)
        self.branch_field(i, "mandal_taluka").select_option(value=taluka)
        self.branch_field(i, "city").fill(city)
        self.branch_field(i, "pincode").fill(pincode)
        self.branch_field(i, "office_premise_type").select_option(value=premise_type)
        if premise_other is not None:
            self.branch_field(i, "office_premise_other").fill(premise_other)

    @allure.step("Remove Branch Office #{index}")
    def remove_branch(self, index: int):
        """Removes the ``index``-th branch card (0-based); the page fades it out first."""
        count = self.branch_cards.count()
        self.branch_remove_button(index).click()
        self.page.wait_for_function(
            "n => document.querySelectorAll('.branch-card').length === n", arg=count - 1
        )

    @allure.step("Fill Authorised Signatory: {name}")
    def fill_authorised_signatory(self, name: str):
        self.authorised_signatory_input.fill(name)
        self.authorised_signatory_input.blur()

    @allure.step("Fill Designation: {designation}")
    def fill_designation(self, designation: str):
        self.designation_input.fill(designation)
        self.designation_input.blur()

    @allure.step("Fill Aadhaar Number")
    def fill_aadhaar(self, aadhaar: str):
        self.aadhaar_input.fill(aadhaar)
        self.aadhaar_input.blur()

    @allure.step("Click 'Save Part A & Continue'")
    def click_submit(self):
        self.submit_button.click()

    @allure.step("Click 'Save Part A & Continue'")
    def click_save_next(self):
        self.submit_button.click()
        self.page.wait_for_load_state()

    @allure.step("Click 'Save Part A & Continue' and handle any alert")
    def click_save_and_handle_alert(self) -> str:
        """Clicks Save and returns the pop-up message (date checks run before submit), or ""."""
        message = self.click_and_handle_alert(self.submit_button, action="dismiss")
        self.page.wait_for_load_state()
        return message
