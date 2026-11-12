import re

import allure

from pages.first_appeal_page import SECOND_APPEAL_URL, FirstAppealPage


class SecondAppealPage(FirstAppealPage):
    """Agency — Second Appeal, FORM-IV (/module/agency/appeals/second.php, "Second Appeal — Commissionerate (State)
    Level", Section 7(2)).

    The page shares FORM-III's header, two-appeals note and journey (``.ap-track``). The form ``#apForm`` is
    offered only after the First Appeal is dismissed; before that the page shows why instead ("Please file
    your First Appeal (FORM-III) first …", "Your First Appeal #N is still pending …").

    The form has the same layout as FORM-III (as seen on dev, 06-Nov-2026): 1–4 Appellant and 5 Details of
    order appealed against are read-only (5 now carries the First Appellate order, ``FAA/<year>/<N>``, and the
    original refusal order ``RA/REJ/<Application ID>/<yyyymmdd>``); 6 grounds, 7 brief facts (≥ 20), 8 relief
    type + relief sought (≥ 10), 9 limitation (auto-calculated), 10 documents (PDF, max 2 MB each — (b) the
    Registering Authority's order and (c) the First Appellate order are required, (d) any other document)
    and the verification. Submitting is "Submit Second — and final — Appeal to the Commissionerate (FORM-IV)".
    """

    # logical document slot → file input name (Section 10)
    DOC_SLOTS = {
        "ra_order":  "doc_ra_order",     # (b) Order of the Registering Authority — REQUIRED
        "fa1_order": "doc_fa1_order",    # (c) Order of the First Appellate Authority — REQUIRED
        "other":     "doc_other",        # (d) Any other document
    }
    SUBMIT_LABEL = "Submit Second — and final — Appeal to the Commissionerate (FORM-IV)"
    ORDER_FIELDS = ("(a) Order Number", "(b) Date of Order", "(c) Authority Passing the Order",
                    "Reason given in the order", "Original Registering Authority Order", "Date of Original Order")
    STEP = "Second Appeal · Commissionerate"

    @property
    def filed_appeal_card(self):
        """The Second Appeal on file, shown instead of the form after filing ('Your Second Appeal …')."""
        return self.page.locator(".ap-card").filter(has=self.page.locator(".ap-title", has_text="Your Second Appeal"))

    @allure.step("Open the Second Appeal (FORM-IV) page")
    def open(self):
        self.navigate(SECOND_APPEAL_URL)
        self.wait_for_load()

    @allure.step("Submit the Second Appeal (accept the confirmation)")
    def submit(self) -> str:
        return super().submit()

    @allure.step("File the Second Appeal")
    def file_appeal(self, data) -> str:
        """Fills the whole form from a ``FirstAppealData`` value object whose documents use this page's
        ``DOC_SLOTS`` and submits it (accepting the confirmation); returns the prompt text."""
        self.fill_appeal(data)
        return self.submit()

    def has_existing_appeal(self) -> bool:
        """Whether a second appeal is already on file (the form is no longer offered)."""
        status = self.journey_status(self.STEP)
        return self.appeal_form.count() == 0 and status.count() > 0 and not re.search(
            "Not filed", status.inner_text())
