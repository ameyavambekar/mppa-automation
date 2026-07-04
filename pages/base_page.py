import allure


class BasePage:
    def __init__(self, page):
        self.page = page

    def navigate(self, url: str):
        self.page.goto(url)

    def wait_for_load(self):
        self.page.wait_for_load_state("networkidle")

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