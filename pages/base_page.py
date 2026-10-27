import allure

from utils.captcha_solver import CAPTCHA_LENGTH, solve_captcha_image


class BasePage:
    def __init__(self, page):
        self.page = page

    def navigate(self, url: str):
        self.page.goto(url)

    def wait_for_load(self):
        self.page.wait_for_load_state("networkidle")

    # ── Image CAPTCHA (agency and admin login pages) ─────────────────────────

    def _wait_for_image_loaded(self, image):
        """Waits until the <img> ``image`` has finished loading its current src."""
        self.page.wait_for_function(
            "img => img.complete && img.naturalWidth > 0",
            arg=image.element_handle(),
            timeout=10000,
        )

    def _wait_for_src_change(self, image, old_src: str):
        """Waits (up to 5s) for the src of ``image`` to differ from ``old_src``."""
        try:
            self.page.wait_for_function(
                "([img, old]) => img.getAttribute('src') !== old",
                arg=[image.element_handle(), old_src],
                timeout=5000,
            )
        except Exception:
            pass

    def read_image_captcha(self, image, refresh, max_attempts: int = 5) -> str:
        """Reads an image CAPTCHA by OCR-ing a screenshot of ``image``.

        The value lives only in the PHP session, so the on-screen image is the
        only source. When OCR doesn't yield exactly 6 characters ``refresh()``
        is called and the image read again, up to ``max_attempts`` times. A
        6-char read can still be wrong — the server rejects it and refreshes.
        """
        text = ""
        for attempt in range(1, max_attempts + 1):
            self._wait_for_image_loaded(image)
            shot = image.screenshot()
            text = solve_captcha_image(shot)
            allure.attach(shot, name=f"captcha attempt {attempt}: {text!r}",
                          attachment_type=allure.attachment_type.PNG)
            if len(text) == CAPTCHA_LENGTH:
                return text
            refresh()
        return text

    @allure.step("Click element and handle alert dialog")
    def click_and_handle_alert(self, locator, action: str = "dismiss", prompt_text: str = None) -> str:
        """
        Clicks the given locator, handles any alert/confirm/prompt dialog that
        appears as a result, and returns the dialog's message string for assertions.

        Follows the project's standard dialog pattern: register a one-shot
        ``dialog`` listener, perform the click, then remove the listener.

        Parameters
        ----------
        locator :
            The Playwright locator to click (e.g. ``self.submit_button``) — the
            element whose click triggers the alert.
        action : str
            How to respond to the dialog: ``"dismiss"`` (default, clicks Cancel /
            closes) or ``"accept"`` (clicks OK / confirms). For confirm dialogs,
            "accept" answers yes and "dismiss" answers no.
        prompt_text : str, optional
            Text to type into a JavaScript ``prompt()`` dialog before accepting.
            Ignored for alert/confirm dialogs.

        Returns
        -------
        str
            The dialog message, or an empty string if no dialog appeared.

        Example
        -------
            message = part_a_page.click_and_handle_alert(
                part_a_page.step_nav_item(2), action="dismiss"
            )
            assert "Please complete Step 1" in message
        """
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            if action == "accept":
                dialog.accept(prompt_text or "")
            else:
                dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        locator.click()
        self.page.remove_listener("dialog", handle_dialog)  # clean up
        return dialog_message[0] if dialog_message else ""

    @allure.step("Go back and handle alert dialog")
    def go_back_and_handle_alert(self, action: str = "dismiss", prompt_text: str = None) -> str:
        """
        Same pattern as ``click_and_handle_alert``, but the trigger is
        ``page.go_back()`` instead of clicking a locator. Use this for
        unsaved-changes prompts raised by the browser's native
        ``beforeunload`` dialog when navigating back with a ``dismiss``
        (stay on page) or ``accept`` (leave the page) response.
        """
        dialog_message = []

        def handle_dialog(dialog):
            dialog_message.append(dialog.message)
            if action == "accept":
                dialog.accept(prompt_text or "")
            else:
                dialog.dismiss()

        self.page.on("dialog", handle_dialog)
        self.page.go_back()
        self.page.remove_listener("dialog", handle_dialog)  # clean up
        return dialog_message[0] if dialog_message else ""