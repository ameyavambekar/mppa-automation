class BasePage:

    BASE_URL = "https://devmppa.sppuef.in/module/agency/auth"

    def __init__(self, page):
        self.page = page

    def navigate(self, url: str):
        self.page.goto(url)

    def wait_for_load(self):
        self.page.wait_for_load_state("networkidle")


