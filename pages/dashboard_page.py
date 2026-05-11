from .base_page import BasePage

class DashboardPage(BasePage):

    # Locators as properties
    @property
    def logout_button(self):
        return self.page.locator("//div[@class='text-blue-200']//following-sibling::a")

    def logout(self):
        self.logout_button.click()