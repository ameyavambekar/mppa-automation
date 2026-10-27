import allure

from pages.base_page import BasePage
from config import INDEX_URL


class IndexPage(BasePage):
    """Page object for the MPPA public landing page (index.php).

    Covers the gov bar, header navbar and mobile drawer, hero + quick facts,
    agency verification tool, portal services cards, preparation checklist,
    8-step registration guide accordion, post-submission statuses, user manual,
    About the Act, footer, back-to-top button and the testing-mode popup.
    """

    # ── Global ───────────────────────────────────────────────────────────────

    @property
    def skip_to_main_link(self):
        return self.page.locator("a.skip-link")

    @property
    def page_loader(self):
        return self.page.locator("#pageLoader")

    @property
    def back_to_top_button(self):
        return self.page.locator("#toTop")

    # ── Top Government Bar ───────────────────────────────────────────────────

    @property
    def gov_bar(self):
        return self.page.locator(".gov-bar")

    @property
    def gov_bar_department_text(self):
        return self.page.locator(".gov-bar > span").first

    @property
    def gov_bar_helpline_text(self):
        return self.page.locator(".gov-bar > span").last

    # ── Header / Navbar ──────────────────────────────────────────────────────

    @property
    def navbar(self):
        return self.page.locator("header#top.navbar")

    @property
    def navbar_brand(self):
        return self.page.locator("header#top a.brand")

    @property
    def navbar_logo_img(self):
        return self.page.locator("header#top .brand-logo img")

    @property
    def navbar_brand_title(self):
        return self.page.locator("header#top .brand-main")

    @property
    def navbar_brand_subtitle(self):
        return self.page.locator("header#top .brand-sub")

    @property
    def nav_links_container(self):
        return self.page.locator("nav.nav-links")

    @property
    def nav_active_link(self):
        """Link currently highlighted by the scroll-spy."""
        return self.page.locator("nav.nav-links a.nav-link.active")

    def nav_link(self, section_id: str):
        """Desktop nav link for a section: home, verify, services, guide, manual, about."""
        return self.page.locator(f"nav.nav-links a.nav-link[href='#{section_id}']")

    @property
    def nav_home_link(self):
        return self.nav_link("home")

    @property
    def nav_verify_agency_link(self):
        return self.nav_link("verify")

    @property
    def nav_services_link(self):
        return self.nav_link("services")

    @property
    def nav_registration_guide_link(self):
        return self.nav_link("guide")

    @property
    def nav_user_manual_link(self):
        return self.nav_link("manual")

    @property
    def nav_about_link(self):
        return self.nav_link("about")

    @property
    def nav_agency_login_button(self):
        return self.page.locator(".nav-cta a[href*='agency/auth/login.php']")

    @property
    def nav_register_agency_button(self):
        return self.page.locator(".nav-cta a[href*='agency/auth/register.php']")

    @property
    def burger_menu_button(self):
        return self.page.locator("#burger")

    # ── Mobile Drawer ────────────────────────────────────────────────────────

    @property
    def drawer(self):
        return self.page.locator("#drawer")

    @property
    def drawer_overlay(self):
        return self.page.locator("#overlay")

    @property
    def drawer_close_button(self):
        return self.page.locator("#drawerClose")

    @property
    def drawer_section_labels(self):
        """'Navigate', 'Portal Access', 'More' headings inside the drawer."""
        return self.page.locator("#drawer .drawer-sec")

    @property
    def drawer_links(self):
        return self.page.locator("#drawer a.dlink")

    def drawer_link(self, href: str):
        """Drawer link by exact href, e.g. '#verify' or 'module/notices.php'."""
        return self.page.locator(f"#drawer a.dlink[href='{href}']")

    @property
    def drawer_super_admin_login_link(self):
        return self.drawer_link("module/admin/auth/login.php?role=super")

    @property
    def drawer_admin_login_link(self):
        return self.drawer_link("module/admin/auth/login.php")

    @property
    def drawer_register_button(self):
        return self.page.locator("#drawer .drawer-foot a[href*='register.php']")

    @property
    def drawer_login_button(self):
        return self.page.locator("#drawer .drawer-foot a[href*='login.php']")

    @property
    def drawer_helpline(self):
        return self.page.locator("#drawer .drawer-help")

    # ── Hero Section ─────────────────────────────────────────────────────────

    @property
    def hero_section(self):
        return self.page.locator("section#home.hero")

    @property
    def hero_badge(self):
        return self.page.locator("#home .hero-badge")

    @property
    def hero_title(self):
        return self.page.locator("#home h1")

    @property
    def hero_subtitle(self):
        return self.page.locator("#home p.lead")

    @property
    def hero_register_button(self):
        return self.page.locator("#home .hero-btns a[href*='register.php']")

    @property
    def hero_verify_button(self):
        return self.page.locator("#home .hero-btns a[href='#verify']")

    @property
    def hero_how_to_register_button(self):
        return self.page.locator("#home .hero-btns a[href='#guide']")

    @property
    def quick_facts_card(self):
        return self.page.locator("#home aside.hero-card")

    @property
    def quick_facts_title(self):
        return self.page.locator("#home .hero-card h2")

    @property
    def quick_facts(self):
        return self.page.locator("#home .facts .fact")

    def quick_fact_value(self, label: str):
        """Fact value (e.g. '7 Days') for a label such as 'To Complete Application'."""
        return self.page.locator("#home .fact").filter(has_text=label).locator("b")

    # ── Verify Agency Section ────────────────────────────────────────────────

    @property
    def verify_section(self):
        return self.page.locator("section#verify")

    @property
    def verify_section_eyebrow(self):
        return self.page.locator("#verify .eyebrow")

    @property
    def verify_section_title(self):
        return self.page.locator("#verify h2.s-title")

    @property
    def verify_panel(self):
        return self.page.locator("#verify .verify")

    @property
    def verify_panel_title(self):
        return self.page.locator("#verify .verify h3")

    @property
    def verify_panel_description(self):
        return self.page.locator("#verify .verify > p:not(.v-hint)")

    @property
    def verify_input(self):
        return self.page.locator("#verifyInput")

    @property
    def verify_button(self):
        return self.page.locator("#verifyBtn")

    @property
    def verify_button_text(self):
        return self.page.locator("#verifyBtnText")

    @property
    def verify_spinner(self):
        return self.page.locator("#verifyBtnText .spinner")

    @property
    def verify_hint_text(self):
        return self.page.locator("#verify p.v-hint")

    @property
    def verify_result_container(self):
        return self.page.locator("#verifyResult")

    @property
    def verify_result_success(self):
        return self.page.locator("#verifyResult .v-ok")

    @property
    def verify_result_fail(self):
        """Failure card: empty input, not found, or server error."""
        return self.page.locator("#verifyResult .v-fail")

    @property
    def verify_result_status_badge(self):
        return self.page.locator("#verifyResult .v-ok span[style*='border-radius:99px']")

    @property
    def verify_result_fields_grid(self):
        return self.page.locator("#verifyResult .v-grid")

    def verify_result_field(self, label: str):
        """Value cell for a result label, e.g. 'Agency Name', 'Valid Until'."""
        return self.page.locator(
            f"//div[@id='verifyResult']//div[@class='vf-l' and normalize-space()='{label}']"
            "/following-sibling::div[contains(@class,'vf-v')]"
        )

    @property
    def verify_result_agency_name(self):
        return self.verify_result_field("Agency Name")

    @property
    def verify_result_certificate_no(self):
        return self.verify_result_field("Certificate No.")

    @property
    def verify_result_agency_type(self):
        return self.verify_result_field("Agency Type")

    @property
    def verify_result_valid_until(self):
        return self.verify_result_field("Valid Until")

    @property
    def verify_result_district(self):
        return self.verify_result_field("District")

    @property
    def verify_result_status(self):
        return self.verify_result_field("Registration Status")

    @property
    def verify_result_advisory(self):
        """Closing advisory line ('safe to engage' / 'Exercise caution')."""
        return self.page.locator("#verifyResult .v-ok > p")

    # ── Portal Services Section ──────────────────────────────────────────────

    @property
    def services_section(self):
        return self.page.locator("section#services")

    @property
    def services_section_eyebrow(self):
        return self.page.locator("#services .eyebrow")

    @property
    def services_section_title(self):
        return self.page.locator("#services h2.s-title")

    @property
    def services_section_subtitle(self):
        return self.page.locator("#services p.s-sub")

    @property
    def services_cards(self):
        return self.page.locator("#services .cards article.card")

    # Card 1: New Agency Registration
    @property
    def new_agency_card(self):
        return self.page.locator("#services article.card.amber")

    @property
    def new_agency_card_title(self):
        return self.new_agency_card.locator("h3")

    @property
    def new_agency_card_desc(self):
        return self.new_agency_card.locator("p")

    @property
    def new_agency_card_register_btn(self):
        return self.new_agency_card.locator("a[href*='register.php']")

    @property
    def new_agency_card_login_btn(self):
        return self.new_agency_card.locator("a[href*='login.php']")

    # Card 2: Verify a Placement Agency
    @property
    def verify_agency_card(self):
        return self.page.locator("#services article.card.green")

    @property
    def verify_agency_card_title(self):
        return self.verify_agency_card.locator("h3")

    @property
    def verify_agency_card_desc(self):
        return self.verify_agency_card.locator("p")

    @property
    def verify_agency_card_btn(self):
        return self.verify_agency_card.locator("a[href*='verify_agency.php']")

    # Card 3: District / Registering Authority
    @property
    def admin_login_card(self):
        return self.page.locator("#services article.card.red")

    @property
    def admin_login_card_title(self):
        return self.admin_login_card.locator("h3")

    @property
    def admin_login_card_desc(self):
        return self.admin_login_card.locator("p")

    @property
    def admin_login_card_btn(self):
        return self.admin_login_card.locator("a[href*='admin/auth/login.php']")

    # ── Step 0 · Preparation Section ─────────────────────────────────────────

    @property
    def prepare_section(self):
        return self.page.locator("section#prepare")

    @property
    def prepare_section_eyebrow(self):
        return self.page.locator("#prepare .eyebrow")

    @property
    def prepare_section_title(self):
        return self.page.locator("#prepare h2.s-title")

    @property
    def prepare_section_subtitle(self):
        return self.page.locator("#prepare p.s-sub")

    @property
    def prepare_cards(self):
        return self.page.locator("#prepare .mcard")

    def prepare_card(self, heading: str):
        """Checklist card by heading: 'Documents', 'Also required', 'General form rules'."""
        return self.page.locator("#prepare .mcard").filter(
            has=self.page.locator("h4", has_text=heading)
        )

    def prepare_card_items(self, heading: str):
        return self.prepare_card(heading).locator("li")

    # ── Registration Guide — 8 Steps Accordion ───────────────────────────────

    @property
    def guide_section(self):
        return self.page.locator("section#guide")

    @property
    def guide_section_eyebrow(self):
        return self.page.locator("#guide .eyebrow")

    @property
    def guide_section_title(self):
        return self.page.locator("#guide h2.s-title")

    @property
    def guide_section_subtitle(self):
        return self.page.locator("#guide p.s-sub")

    @property
    def expand_all_button(self):
        return self.page.locator("#expandAll")

    @property
    def collapse_all_button(self):
        return self.page.locator("#collapseAll")

    @property
    def stepper(self):
        return self.page.locator("#guide ol.stepper")

    @property
    def all_steps(self):
        return self.page.locator("#guide ol.stepper > li.st")

    @property
    def all_step_details(self):
        return self.page.locator("#guide details.step")

    def step(self, step_number: int):
        """<li> for step 1–8."""
        return self.all_steps.nth(step_number - 1)

    def step_num(self, step_number: int):
        return self.step(step_number).locator(".st-num")

    def step_details(self, step_number: int):
        """<details> element; its `open` attribute reflects expanded state."""
        return self.step(step_number).locator("details.step")

    def step_summary(self, step_number: int):
        """Clickable <summary> header that toggles the step."""
        return self.step(step_number).locator("summary")

    def step_title(self, step_number: int):
        return self.step(step_number).locator(".st-h")

    def step_desc(self, step_number: int):
        return self.step(step_number).locator(".st-d")

    def step_body(self, step_number: int):
        return self.step(step_number).locator(".step-body")

    def step_column_headings(self, step_number: int):
        return self.step(step_number).locator(".step-body h5")

    def step_list_items(self, step_number: int):
        return self.step(step_number).locator(".step-body li")

    def step_rule_items(self, step_number: int):
        return self.step(step_number).locator(".step-body li.rule")

    def step_ok_items(self, step_number: int):
        return self.step(step_number).locator(".step-body li.ok")

    @property
    def enclosures_upload_tip(self):
        """'Upload rule: PDF of max 2 MB' tip inside step 6."""
        return self.step(6).locator(".tip")

    @property
    def start_registration_cta_button(self):
        return self.page.locator("#guide a[href*='register.php']")

    @property
    def read_user_manual_button(self):
        return self.page.locator("#guide a[href='#manual']")

    # ── After Submission Section ─────────────────────────────────────────────

    @property
    def after_section(self):
        return self.page.locator("section#after")

    @property
    def after_section_eyebrow(self):
        return self.page.locator("#after .eyebrow")

    @property
    def after_section_title(self):
        return self.page.locator("#after h2.s-title")

    @property
    def after_section_subtitle(self):
        return self.page.locator("#after p.s-sub")

    @property
    def status_cards(self):
        return self.page.locator("#after .status-grid .stat")

    def status_card(self, status: str):
        """Status card: 'Submitted', 'Approved', 'Rejected', 'Suspended'."""
        return self.page.locator("#after .stat").filter(
            has=self.page.locator("i", has_text=status)
        )

    def status_card_desc(self, status: str):
        return self.status_card(status).locator("p")

    @property
    def after_inspection_note(self):
        return self.page.locator("#after .manual-note")

    # ── User Manual Section ──────────────────────────────────────────────────

    @property
    def manual_section(self):
        return self.page.locator("section#manual")

    @property
    def manual_section_eyebrow(self):
        return self.page.locator("#manual .eyebrow")

    @property
    def manual_section_title(self):
        return self.page.locator("#manual h2.s-title")

    @property
    def manual_card_title(self):
        return self.page.locator("#manual .manual h3")

    @property
    def manual_card_desc(self):
        return self.page.locator("#manual .manual p")

    @property
    def manual_view_button(self):
        return self.page.locator("#manual .manual-act a").first

    @property
    def manual_download_button(self):
        return self.page.locator("#manual .manual-act a").last

    # ── About the Act Section ────────────────────────────────────────────────

    @property
    def about_section(self):
        return self.page.locator("section#about")

    @property
    def about_section_eyebrow(self):
        return self.page.locator("#about .eyebrow")

    @property
    def about_section_title(self):
        return self.page.locator("#about h2.s-title")

    @property
    def about_act_banner(self):
        return self.page.locator("#about .act")

    @property
    def about_act_badge(self):
        return self.page.locator("#about .act-badge")

    @property
    def about_act_title(self):
        return self.page.locator("#about .act h3")

    @property
    def about_act_description(self):
        return self.page.locator("#about .act p")

    def about_act_box_value(self, label: str):
        """Value (e.g. '5 Years') for 'Certificate Validity' / 'Renewal Notice Period'."""
        return self.page.locator("#about .act-box").filter(has_text=label).locator("b")

    @property
    def about_validity_value(self):
        return self.about_act_box_value("Certificate Validity")

    @property
    def about_renewal_period_value(self):
        return self.about_act_box_value("Renewal Notice Period")

    @property
    def about_read_guidelines_button(self):
        return self.page.locator("#about a[href*='guidelines.php']")

    # ── Footer ───────────────────────────────────────────────────────────────

    @property
    def footer(self):
        return self.page.locator("footer")

    def _footer_column(self, heading: str):
        return self.page.locator("footer .f-grid > div").filter(
            has=self.page.locator("h4", has_text=heading)
        )

    def footer_link(self, text: str):
        return self.page.locator("footer a", has_text=text)

    @property
    def footer_portal_heading(self):
        return self._footer_column("MPPA Portal").locator("h4")

    @property
    def footer_portal_description(self):
        return self._footer_column("MPPA Portal").locator("p")

    @property
    def footer_contact(self):
        """Support email, helpline and hours block."""
        return self.page.locator("footer .f-contact")

    @property
    def footer_quick_links_heading(self):
        return self._footer_column("Quick Links").locator("h4")

    @property
    def footer_quick_links(self):
        return self._footer_column("Quick Links").locator("a")

    @property
    def footer_new_registration_link(self):
        return self.footer_link("New Registration")

    @property
    def footer_agency_login_link(self):
        return self._footer_column("Quick Links").locator("a", has_text="Agency Login")

    @property
    def footer_verify_agency_link(self):
        return self.footer_link("Verify Agency")

    @property
    def footer_registration_guide_link(self):
        return self.footer_link("Registration Guide")

    @property
    def footer_user_manual_link(self):
        return self.footer_link("Registration User Manual")

    @property
    def footer_download_manual_link(self):
        return self.footer_link("Download Manual (PDF)")

    @property
    def footer_guidelines_link(self):
        return self.page.locator("footer a[href='module/guidelines.php']")

    @property
    def footer_contact_us_link(self):
        return self.footer_link("Contact Us")

    @property
    def footer_notice_board_link(self):
        return self.footer_link("Notice Board")

    @property
    def footer_officials_heading(self):
        return self._footer_column("Officials").locator("h4")

    @property
    def footer_admin_ra_login_link(self):
        return self.footer_link("Admin / RA Login")

    @property
    def footer_super_admin_login_link(self):
        return self.footer_link("Super Admin Login")

    @property
    def footer_faq_link(self):
        return self.page.locator("footer a[href$='#faq']")

    @property
    def footer_terms_and_conditions_link(self):
        return self.page.locator("footer a[href$='#tnc']")

    @property
    def footer_copyright_text(self):
        return self.page.locator("footer .f-bottom span").first

    @property
    def footer_act_reference_text(self):
        return self.page.locator("footer .f-bottom span").last

    # ── Testing Mode Popup & Chip ────────────────────────────────────────────

    @property
    def testing_mode_chip(self):
        return self.page.locator("#tpChip")

    @property
    def testing_modal(self):
        """Popup root; carries class 'show' while open."""
        return self.page.locator("#tpop")

    @property
    def testing_modal_card(self):
        return self.page.locator("#tpop .tp-card")

    @property
    def testing_modal_close_button(self):
        return self.page.locator("#tpop button.tp-x")

    @property
    def testing_modal_badge(self):
        return self.page.locator("#tpop .tp-badge")

    @property
    def testing_modal_title(self):
        return self.page.locator("#tpTitle")

    @property
    def testing_modal_text(self):
        return self.page.locator("#tpop .tp-text")

    @property
    def testing_modal_list_items(self):
        return self.page.locator("#tpop .tp-list li")

    @property
    def testing_modal_continue_button(self):
        return self.page.locator("#tpop button.tp-btn")

    @property
    def testing_modal_footer_text(self):
        return self.page.locator("#tpop .tp-foot")

    # ── Actions ──────────────────────────────────────────────────────────────

    @allure.step("Open the MPPA Index / Landing Page")
    def open(self, url: str = None):
        self.navigate(url or INDEX_URL)
        self.wait_for_load()

    @allure.step("Dismiss Testing Mode popup if visible")
    def dismiss_testing_modal(self):
        # Popup opens on a 400ms timer and only once per session.
        try:
            self.testing_modal_continue_button.wait_for(state="visible", timeout=2000)
        except Exception:
            return
        self.testing_modal_continue_button.click()
        self.testing_modal_card.wait_for(state="hidden")

    @allure.step("Close Testing Mode popup via '×'")
    def close_testing_modal(self):
        self.testing_modal_close_button.click()
        self.testing_modal_card.wait_for(state="hidden")

    @allure.step("Open Testing Mode popup via bottom-left chip")
    def open_testing_modal(self):
        self.testing_mode_chip.click()
        self.testing_modal_card.wait_for(state="visible")

    @allure.step("Verify placement agency with ID/Certificate: '{query}'")
    def verify_agency(self, query: str):
        self.verify_input.fill(query)
        self.verify_button.click()

    @allure.step("Verify placement agency via Enter key: '{query}'")
    def verify_agency_with_enter(self, query: str):
        self.verify_input.fill(query)
        self.verify_input.press("Enter")

    @allure.step("Click navbar link '#{section_id}'")
    def click_nav_link(self, section_id: str):
        self.nav_link(section_id).click()

    @allure.step("Click navbar 'Agency Login'")
    def click_nav_login(self):
        self.nav_agency_login_button.click()

    @allure.step("Click navbar 'Register Agency'")
    def click_nav_register(self):
        self.nav_register_agency_button.click()

    @allure.step("Open mobile menu drawer")
    def open_drawer(self):
        self.burger_menu_button.click()
        self.drawer_close_button.wait_for(state="visible")

    @allure.step("Close mobile menu drawer")
    def close_drawer(self):
        self.drawer_close_button.click()

    @allure.step("Click drawer link '{href}'")
    def click_drawer_link(self, href: str):
        self.drawer_link(href).click()

    @allure.step("Click Hero 'New Agency Registration'")
    def click_hero_register(self):
        self.hero_register_button.click()

    @allure.step("Click Hero 'Verify an Agency'")
    def click_hero_verify(self):
        self.hero_verify_button.click()

    @allure.step("Click Hero 'How to Register'")
    def click_hero_how_to_register(self):
        self.hero_how_to_register_button.click()

    @allure.step("Click Services 'Register Now'")
    def click_services_register(self):
        self.new_agency_card_register_btn.click()

    @allure.step("Click Services 'Login'")
    def click_services_login(self):
        self.new_agency_card_login_btn.click()

    @allure.step("Click Services 'Verify Agency'")
    def click_services_verify_agency(self):
        self.verify_agency_card_btn.click()

    @allure.step("Click Services 'Admin Login'")
    def click_services_admin_login(self):
        self.admin_login_card_btn.click()

    @allure.step("Toggle registration guide step {step_number}")
    def toggle_step(self, step_number: int):
        self.step_summary(step_number).click()

    @allure.step("Expand all registration guide steps")
    def expand_all_steps(self):
        self.expand_all_button.click()

    @allure.step("Collapse all registration guide steps")
    def collapse_all_steps(self):
        self.collapse_all_button.click()

    @allure.step("Click 'Start Registration' CTA in guide section")
    def click_start_registration_cta(self):
        self.start_registration_cta_button.click()

    @allure.step("Click 'Read User Manual' in guide section")
    def click_read_user_manual(self):
        self.read_user_manual_button.click()

    @allure.step("Click 'Read Guidelines' in About section")
    def click_about_read_guidelines(self):
        self.about_read_guidelines_button.click()

    @allure.step("Click 'Back to top'")
    def click_back_to_top(self):
        self.back_to_top_button.click()
