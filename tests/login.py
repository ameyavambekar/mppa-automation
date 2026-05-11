def test_successful_login(login_page, dashboard_page):
    login_page.open()
    login_page.login("User_3", "!!June@1993")
    dashboard_page.logout()


def test_invalid_credentials(login_page):
    login_page.open()
    login_page.login("wrong", "!!June@1993")

    login_page.error_message.wait_for()
    assert login_page.error_message.is_visible()