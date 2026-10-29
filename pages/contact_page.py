import allure

from config import MODULE_ROOT
from pages.base_page import BasePage

CONTACT_URL = f"{MODULE_ROOT}/contact.php"


class ContactPage(BasePage):
    """Page object for the Contact Us page (module/contact.php) — public, the same logged in or out.

    A hero (``.ct-hero``), the "Send Us a Message" form (``#contactForm``, alert ``#formAlert``,
    button ``#ctBtn``, counter ``#charLeft``) and a right-hand column of ``.wcard`` cards
    ("Contact Information" with ``.info-item`` rows, "Office Hours" with ``.hours-table``) plus an
    "Expected Response Time" box. The fields strip what they refuse as you type (mobile and
    Application ID keep digits only; the message drops HTML tags).
    """

    HERO_LABEL = "SUPPORT & ENQUIRIES"  # upper-cased by CSS
    HEADING = "Contact Us"
    INTRO = "Reach out to our helpdesk for any technical issues, registration queries, or general assistance."
    FORM_TITLE = "Send Us a Message"
    CONTACT_INFO_TITLE = "Contact Information"
    OFFICE_HOURS_TITLE = "Office Hours"
    RESPONSE_TIME_TITLE = "Expected Response Time"
    FIELD_LABELS = ("Full Name *", "Email ID *", "Mobile Number", "Application ID (if any)", "Query Type *",
                    "Your Message *")
    QUERY_TYPES = ("— Select Query Type —", "New Registration", "Licence Renewal", "Document Upload Issue",
                   "Application Status", "Login / Account Issue", "Fee Payment Issue", "Appeal Related", "Other")
    SEND_LABEL = "Send Message"
    SENDING_LABEL = "Sending…"
    MESSAGE_MAX_LENGTH = 500
    SENT_HEADING = "Message sent successfully!"
    SENT_TEXT = "Our team will respond to your query within 2 working days."
    INFO = {"Helpdesk (Toll Free)": "1800-XXX-XXXX",
            "Email Support": "support@placementportal.gov.in",
            "Fax": "+91-11-XXXX-XXXX"}
    ADDRESS_LINES = ("Skills, Employment, Entrepreneurship and Innovation Department", "Government of Maharashtra",
                     "Mantralaya, Madam Cama Road", "Mumbai – 400032")
    PHONE_HREF = "tel:1800-XXX-XXXX"
    EMAIL_HREF = "mailto:support@placementportal.gov.in"
    OFFICE_HOURS = (("Monday – Friday", "9:00 AM – 6:00 PM"), ("Saturday & Sunday", "Closed"))
    HOLIDAYS_NOTE = "Public holidays as per the Government of India notifications."
    RESPONSE_TIMES = ("Email queries: within 2 working days", "Phone helpdesk: Immediate assistance during office hours",
                      "Portal complaints are resolved within 5 working days")

    @staticmethod
    def characters_left(n: int) -> str:
        return f"{n} characters remaining"

    # ── Top bar ───────────────────────────────────────────────────────────────

    def nav_link(self, label: str):
        return self.page.locator(".nav-links a", has_text=label)

    def top_bar_link(self, label: str):
        return self.page.locator(".nav-right").get_by_role("link", name=label, exact=True)

    @property
    def user_text(self):
        """'<username> (<Application ID>)' while logged in."""
        return self.page.locator(".nav-right .nav-user-text")

    # ── Hero ──────────────────────────────────────────────────────────────────

    @property
    def hero_label(self):
        return self.page.locator(".ct-hero .ct-hero-label")

    @property
    def heading(self):
        return self.page.locator(".ct-hero h1")

    @property
    def intro(self):
        return self.page.locator(".ct-hero p")

    # ── Cards ─────────────────────────────────────────────────────────────────

    def card(self, title: str):
        return self.page.locator(".wcard").filter(has=self.page.locator(".sec-title", has_text=title))

    @property
    def card_titles(self):
        return self.page.locator(".wcard .sec-title")

    def info_value(self, label: str):
        """The value next to a Contact Information label, e.g. 'Fax'."""
        return self.card(self.CONTACT_INFO_TITLE).locator(".info-item").filter(
            has=self.page.locator(".info-label", has_text=label)).locator(".info-val")

    @property
    def phone_link(self):
        return self.card(self.CONTACT_INFO_TITLE).locator("a[href^='tel:']")

    @property
    def email_link(self):
        return self.card(self.CONTACT_INFO_TITLE).locator("a[href^='mailto:']")

    @property
    def office_hours_rows(self):
        return self.card(self.OFFICE_HOURS_TITLE).locator(".hours-table tr")

    @property
    def office_hours_card(self):
        return self.card(self.OFFICE_HOURS_TITLE)

    @property
    def response_time_box(self):
        return self.page.locator("div").filter(
            has=self.page.locator(":scope > strong", has_text=self.RESPONSE_TIME_TITLE))

    # ── Form ──────────────────────────────────────────────────────────────────

    @property
    def form(self):
        return self.page.locator("#contactForm")

    @property
    def field_labels(self):
        return self.form.locator(".ct-label")

    @property
    def name_input(self):
        return self.form.locator("input[name='name']")

    @property
    def email_input(self):
        return self.form.locator("input[name='email']")

    @property
    def mobile_input(self):
        return self.form.locator("input[name='mobile']")

    @property
    def application_id_input(self):
        return self.form.locator("input[name='reg_id']")

    @property
    def query_type_select(self):
        return self.form.locator("select[name='query_type']")

    @property
    def query_type_options(self):
        return self.query_type_select.locator("option")

    @property
    def message_input(self):
        return self.form.locator("textarea[name='message']")

    @property
    def character_note(self):
        """'<n> characters remaining' below Your Message."""
        return self.form.locator(".char-note")

    @property
    def send_button(self):
        return self.page.locator("#ctBtn")

    @property
    def alert(self):
        """The result box above the form; class ``success`` once a message is sent."""
        return self.page.locator("#formAlert")

    # ── Actions ───────────────────────────────────────────────────────────────

    @allure.step("Open the Contact Us page")
    def open(self):
        self.navigate(CONTACT_URL)
        self.wait_for_load()

    @allure.step("Fill in the message form")
    def fill_form(self, name: str = None, email: str = None, mobile: str = None, application_id: str = None,
                  query_type: str = None, message: str = None):
        """Fills the given fields; ``None`` leaves a field as it is."""
        for field, value in ((self.name_input, name), (self.email_input, email), (self.mobile_input, mobile),
                             (self.application_id_input, application_id), (self.message_input, message)):
            if value is not None:
                field.fill(value)
        if query_type is not None:
            self.query_type_select.select_option(label=query_type)

    @allure.step("Click 'Send Message'")
    def send(self):
        self.send_button.click()
