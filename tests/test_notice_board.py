import re

import allure
import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import expect

from pages.notice_board_page import NoticeBoardPage
from test_data.notice_board_factory import NoticeBoardFactory, NoticeSearchData
from utils.aio import aio_case

STORY = "Notice Board"


def _matching(cards: list[dict], query: str) -> list[str]:
    """Titles of the cards whose title or text contain ``query``, ignoring case (what the search should show)."""
    q = query.lower()
    return [c["title"] for c in cards if q in c["title"].lower() or q in c["body"].lower()]


def _of_type(cards: list[dict], notice_type: str) -> list[dict]:
    return [c for c in cards if c["type"] == notice_type]


def _active_class(notice_type: str) -> re.Pattern:
    """The highlighted pill's class: ``active`` for All, ``active-<type>`` for the others."""
    name = "active" if notice_type == "all" else f"active-{notice_type}"
    return re.compile(rf"(^|\s){name}(\s|$)")


def _expect_board_shows(board: NoticeBoardPage, titles: list[str]) -> None:
    """The board lists exactly ``titles`` (in order) and the count badge shows how many."""
    expect(board.notice_cards.locator(".notice-title")).to_have_text(titles)
    expect(board.count_badge).to_have_text(str(len(titles)))


# ---------------------------------------------------------------------------
# TC-531  Page layout
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-531")
@allure.story(STORY)
@allure.title("TC-531: Notice Board shows the heading, count, filter pills, search and one card per active notice")
def test_tc531_layout(agency_notice_board: NoticeBoardPage):
    """
    Given notices have been published
    When  I open the Notice Board
    Then  I see the heading, the intro, the count badge, the filter pills with All highlighted,
          the search box and button, and one card per notice

    Notion: KAN-TC-531 | KAN-41 AC-1
    """
    board = agency_notice_board

    with allure.step("Verify the hero"):
        expect(board.board_heading).to_have_text("Official Notice Board")
        expect(board.intro).to_have_text(NoticeBoardPage.INTRO)
        expect(board.count_badge).to_have_text(re.compile(r"^\d+$"))

    with allure.step("Verify the filter bar"):
        expect(board.filter_pills).to_have_text(list(NoticeBoardPage.FILTERS))
        expect(board.pill("all")).to_have_class(_active_class("all"))
        expect(board.highlighted_pills).to_have_count(1)
        expect(board.search_input).to_have_attribute("placeholder", NoticeBoardPage.SEARCH_PLACEHOLDER)
        expect(board.search_button).to_have_text(NoticeBoardPage.SEARCH_LABEL)

    with allure.step("Verify there is one card per notice and the count badge matches"):
        cards = board.notice_cards.count()
        assert cards > 0, "No notices are published"
        expect(board.count_badge).to_have_text(str(cards))


# ---------------------------------------------------------------------------
# TC-532  Card content
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-532")
@allure.story(STORY)
@allure.title("TC-532: Each notice card shows its badge, date, title, text and issuing department")
def test_tc532_card_content(agency_notice_board: NoticeBoardPage):
    """
    Given notices have been published, at least one with an issuing department
    When  I look at the notice cards
    Then  each shows a badge, the date (dd Mon yyyy), the title and the full text; a notice with a
          department shows it; each badge type has its own colour

    Notion: KAN-TC-532 | KAN-41 AC-2, Display Rules
    """
    board = agency_notice_board
    cards = board.read_cards()

    with allure.step("Verify every card shows a badge, date, title and text"):
        for card in cards:
            assert card["badge"] in NoticeBoardFactory.BADGES, f"{card['title']!r}: badge {card['badge']!r}"
            assert NoticeBoardFactory.BADGES[card["badge"]] == card["type"], \
                f"{card['title']!r}: badge {card['badge']} on a type-{card['type']} card"
            assert re.match(NoticeBoardFactory.DATE_PATTERN, card["date"]), \
                f"{card['title']!r}: date {card['date']!r} is not dd Mon yyyy"
            assert card["title"], "A card has no title"
            assert card["body"] and not card["body"].endswith("…"), f"{card['title']!r}: text missing or cut"

    with allure.step("Verify a notice with a department shows it"):
        index = next((i for i, c in enumerate(cards) if c["dept"]), None)
        assert index is not None, "No notice has an issuing department"
        expect(board.card_part(index, "notice-dept")).to_be_visible()

    with allure.step("Verify each badge type has its own colour"):
        colours = {}
        for card in cards:
            colours.setdefault(card["badge"], set()).add(card["badge_colour"])
        assert all(len(c) == 1 for c in colours.values()), f"A badge type has several colours: {colours}"
        assert len({c.pop() for c in colours.values()}) == len(colours), f"Badge types share a colour: {colours}"


# ---------------------------------------------------------------------------
# TC-533  Pinned notices first
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-533")
@allure.story(STORY)
@allure.title("TC-533: Pinned notices are shown first and marked \"Pinned\"")
def test_tc533_pinned_first(agency_notice_board: NoticeBoardPage):
    """
    Given at least one active notice is pinned and one is not
    When  I open the Notice Board
    Then  every pinned notice comes before every other notice, and only pinned notices show "Pinned"

    Notion: KAN-TC-533 | KAN-41 AC-3
    """
    board = agency_notice_board
    cards = board.read_cards()
    pinned = [c["pinned"] for c in cards]
    assert True in pinned and False in pinned, "Needs a pinned and an unpinned notice"

    with allure.step("Verify pinned notices come first"):
        assert pinned == sorted(pinned, reverse=True), \
            f"Order (pinned?): {list(zip([c['title'] for c in cards], pinned))}"

    with allure.step("Verify a pinned notice shows \"Pinned\""):
        first = pinned.index(True)
        expect(board.card_part(first, "pin-icon")).to_contain_text("Pinned")
        expect(board.notice_cards.nth(first)).to_have_class(re.compile(r"\bpinned\b"))

    with allure.step("Verify a notice that is not pinned does not show \"Pinned\""):
        expect(board.card_part(pinned.index(False), "pin-icon")).to_have_count(0)


# ---------------------------------------------------------------------------
# TC-534  Filter pills
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-534")
@allure.story(STORY)
@allure.title("TC-534: Filter pills show only notices of the chosen type and update the count")
def test_tc534_filter_pills(agency_notice_board: NoticeBoardPage):
    """
    Given notices of each type have been published
    When  I click each filter pill in turn, then All
    Then  only notices of that type are shown, the pill is highlighted and the count matches;
          All shows every notice again

    Notion: KAN-TC-534 | KAN-41 AC-4
    """
    board = agency_notice_board
    cards = board.read_cards()

    for label, notice_type in NoticeBoardPage.FILTERS.items():
        if notice_type == "all":
            continue
        with allure.step(f"Click \"{label}\" and verify only {label.upper()} notices are shown"):
            board.click_pill(label)
            expected = [c["title"] for c in _of_type(cards, notice_type)]
            assert expected, f"No {label.upper()} notice is published"
            _expect_board_shows(board, expected)
            expect(board.pill(notice_type)).to_have_class(_active_class(notice_type))
            expect(board.highlighted_pills).to_have_count(1)

    with allure.step("Click \"All\" and verify every notice is shown again"):
        board.click_pill("All")
        _expect_board_shows(board, [c["title"] for c in cards])
        expect(board.pill("all")).to_have_class(_active_class("all"))


# ---------------------------------------------------------------------------
# TC-535  Search
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-535")
@allure.story(STORY)
@allure.title("TC-535: Search shows notices whose title or text contain the search text, ignoring case")
def test_tc535_search(agency_notice_board: NoticeBoardPage, title_word_data: NoticeSearchData,
                      title_word_in_capitals_data: NoticeSearchData, body_only_word_data: NoticeSearchData):
    """
    Given notices have been published
    When  I search for a word from a notice title, then the same word in capitals, then a word that
          appears only in a notice's text
    Then  each time only notices whose title or text contain the word are shown, the count matches
          and the word stays in the search box

    Notion: KAN-TC-535 | KAN-41 AC-5 | data: title_word, title_word_in_capitals, body_only_word
    """
    board = agency_notice_board
    cards = board.read_cards()
    expected = _matching(cards, title_word_data.query)
    assert expected, f"No notice contains {title_word_data.query!r}"

    with allure.step(f"Search for '{title_word_data.query}' and verify the matching notices"):
        board.search_with_button(title_word_data.query)
        _expect_board_shows(board, expected)
        expect(board.search_input).to_have_value(title_word_data.query)

    with allure.step(f"Search for '{title_word_in_capitals_data.query}' and verify the same notices"):
        board.search_with_button(title_word_in_capitals_data.query)
        _expect_board_shows(board, expected)

    with allure.step(f"Search for '{body_only_word_data.query}' (only in a notice's text)"):
        body_only = _matching(cards, body_only_word_data.query)
        assert body_only and not any(body_only_word_data.query in t.lower() for t in body_only), \
            f"{body_only_word_data.query!r} must appear in a notice's text but in no title"
        board.search_with_button(body_only_word_data.query)
        _expect_board_shows(board, body_only)


# ---------------------------------------------------------------------------
# TC-536  Search within a filter
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-536")
@allure.story(STORY)
@allure.title("TC-536: Search within a filter shows only matching notices of that type")
def test_tc536_search_within_filter(agency_notice_board: NoticeBoardPage, word_within_alert_data: NoticeSearchData):
    """
    Given an ALERT notice and a notice of another type both contain the search word
    When  I click "Alert" and search for the word
    Then  only the ALERT notice is shown, "Alert" stays highlighted and the count matches

    Notion: KAN-TC-536 | KAN-41 AC-5 | data: word_within_alert
    """
    board = agency_notice_board
    data = word_within_alert_data
    cards = board.read_cards()
    expected = _matching(_of_type(cards, data.notice_type), data.query)
    assert expected and len(_matching(cards, data.query)) > len(expected), \
        f"{data.query!r} must be in an ALERT notice and in a notice of another type"

    with allure.step("Click \"Alert\""):
        board.click_pill("Alert")
        _expect_board_shows(board, [c["title"] for c in _of_type(cards, data.notice_type)])

    with allure.step(f"Search for '{data.query}' and verify only the matching ALERT notices"):
        board.search_with_button(data.query)
        _expect_board_shows(board, expected)
        expect(board.pill(data.notice_type)).to_have_class(_active_class(data.notice_type))
        expect(board.search_input).to_have_value(data.query)


# ---------------------------------------------------------------------------
# TC-537  Search with no match
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-537")
@allure.story(STORY)
@allure.title("TC-537: Search with no match shows \"No notices found for \"<text>\".\" and a count of 0")
def test_tc537_search_no_match(agency_notice_board: NoticeBoardPage, no_match_data: NoticeSearchData):
    """
    Given no notice contains the search text
    When  I search for it
    Then  no cards are shown, the count is 0 and the page reads 'No notices found for "<text>".'

    Notion: KAN-TC-537 | KAN-41 AC-6 | data: no_match
    """
    board = agency_notice_board
    assert not _matching(board.read_cards(), no_match_data.query), f"A notice contains {no_match_data.query!r}"

    with allure.step(f"Search for '{no_match_data.query}'"):
        board.search_with_button(no_match_data.query)

    with allure.step("Verify the empty result"):
        expect(board.notice_cards).to_have_count(0)
        expect(board.count_badge).to_have_text("0")
        expect(board.empty_state_text).to_have_text(NoticeBoardPage.no_notices_for(no_match_data.query))


# ---------------------------------------------------------------------------
# TC-538  View Attachment
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-538")
@allure.story(STORY)
@allure.title("TC-538: \"View Attachment\" opens the notice's attached file in a new tab")
def test_tc538_view_attachment(agency_notice_board: NoticeBoardPage):
    """
    Given at least one notice has a PDF or image attachment
    When  I click "View Attachment" on each such notice
    Then  a new tab opens with the attached PDF or image, not an error page

    Notion: KAN-TC-538 | KAN-41 AC-7

    Known defect (29-Oct-2026): both attachments on dev answer 404 "File not found." — this test fails.
    """
    board = agency_notice_board
    page = board.page
    links = board.attachment_links
    assert links.count(), "No notice has an attachment"

    for i in range(links.count()):
        link = links.nth(i)
        with allure.step(f"Click \"View Attachment\" #{i + 1} and verify the file opens in a new tab"):
            expect(link).to_have_attribute("target", "_blank")
            with page.context.expect_event("response", lambda r: "serve_enclosure.php" in r.url) as response_info, \
                    page.expect_popup() as popup_info:
                link.click()
            response, popup = response_info.value, popup_info.value
            try:
                assert response.ok, f"{response.url} returned {response.status}"
                content_type = response.headers.get("content-type", "")
                assert content_type.startswith(("application/pdf", "image/")), \
                    f"{response.url} is {content_type!r}, not a PDF or image"
            finally:
                popup.close()


# ---------------------------------------------------------------------------
# TC-539  Logged out
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-539")
@allure.story(STORY)
@allure.title("TC-539: Logged-out visitors see the same Notice Board")
def test_tc539_logged_out(logged_out_notice_board, word_within_alert_data: NoticeSearchData):
    """
    Given I am logged out
    When  I open the Notice Board, then click "Alert" and search for a word
    Then  I see the same notices, count, filters and search as a logged-in agency, with Login and
          Register in the top bar, and filter and search work

    Notion: KAN-TC-539 | KAN-41 AC-8 | data: word_within_alert
    """
    board, agency_titles = logged_out_notice_board
    data = word_within_alert_data

    with allure.step("Verify the top bar shows Login and Register"):
        expect(board.top_bar_link("Login")).to_be_visible()
        expect(board.top_bar_link("Register")).to_be_visible()
        expect(board.top_bar_link("Logout")).to_have_count(0)

    with allure.step("Verify the same notices, count, filters and search as for an agency"):
        expect(board.board_heading).to_have_text("Official Notice Board")
        _expect_board_shows(board, agency_titles)
        expect(board.filter_pills).to_have_text(list(NoticeBoardPage.FILTERS))
        expect(board.search_input).to_be_visible()

    with allure.step(f"Click \"Alert\", search for '{data.query}' and verify the matching ALERT notices"):
        cards = board.read_cards()
        board.click_pill("Alert")
        board.search_with_button(data.query)
        _expect_board_shows(board, _matching(_of_type(cards, data.notice_type), data.query))
        expect(board.pill(data.notice_type)).to_have_class(_active_class(data.notice_type))


# ---------------------------------------------------------------------------
# TC-540  HTML and special characters
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-540")
@allure.story(STORY)
@allure.title("TC-540: Search refuses HTML and special characters")
def test_tc540_search_refuses_html(agency_notice_board: NoticeBoardPage, html_tag_data: NoticeSearchData):
    """
    Given I am on the Notice Board
    When  I search for text with HTML, then open the board with that text in the URL
    Then  the browser does not send the search and names the rule; from the URL, all notices are
          shown with an empty search box

    Notion: KAN-TC-540 | KAN-41 EC-1, Display Rules | data: html_tag

    Known defect (29-Oct-2026): the search box's pattern attribute is not a valid regular expression in
    current browsers (they compile it with the v flag, where an unescaped ( ) { } is invalid), so the
    browser ignores it and sends the search — this test fails.
    """
    board = agency_notice_board
    page = board.page
    all_titles = [c["title"] for c in board.read_cards()]
    url = page.url

    with allure.step(f"Enter '{html_tag_data.query}'"):
        board.search_input.fill(html_tag_data.query)

    with allure.step("Verify the browser refuses the text and names the rule"):
        assert not board.search_input.evaluate("e => e.checkValidity()"), \
            f"The browser accepts {html_tag_data.query!r}, so the search is sent"
        expect(board.search_input).to_have_attribute("title", html_tag_data.expected_error)

    with allure.step("Click Search and verify the search is not sent"):
        with pytest.raises(PlaywrightTimeoutError):
            with page.expect_navigation(timeout=3000):
                board.search_button.click()
        expect(page).to_have_url(url)

    with allure.step(f"Open the board with q={html_tag_data.query} in the URL"):
        board.open_with("all", html_tag_data.query)

    with allure.step("Verify all notices are shown and the search box is empty"):
        _expect_board_shows(board, all_titles)
        expect(board.search_input).to_have_value("")


# ---------------------------------------------------------------------------
# TC-541  100-character limit
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-541")
@allure.story(STORY)
@allure.title("TC-541: Search box accepts at most 100 characters")
def test_tc541_search_max_length(agency_notice_board: NoticeBoardPage, over_max_length_data: NoticeSearchData):
    """
    Given I am on the Notice Board
    When  I type 101 characters into the search box
    Then  only the first 100 are kept

    Notion: KAN-TC-541 | KAN-41 Display Rules | data: over_max_length
    """
    board = agency_notice_board

    with allure.step(f"Type {len(over_max_length_data.query)} characters into the search box"):
        board.search_input.press_sequentially(over_max_length_data.query)

    with allure.step(f"Verify only the first {NoticeBoardPage.SEARCH_MAX_LENGTH} are kept"):
        expect(board.search_input).to_have_value(over_max_length_data.query[:NoticeBoardPage.SEARCH_MAX_LENGTH])


# ---------------------------------------------------------------------------
# TC-542  Unknown filter type
# ---------------------------------------------------------------------------
@aio_case("KAN-TC-542")
@allure.story(STORY)
@allure.title("TC-542: Unknown filter type shows \"No notices found.\" with no pill highlighted")
def test_tc542_unknown_type(agency_notice_board: NoticeBoardPage, unknown_type_data: NoticeSearchData):
    """
    Given I am on the Notice Board
    When  I open it with an unknown type in the URL (?type=bogus)
    Then  no pill is highlighted, the count is 0 and the page reads "No notices found."

    Notion: KAN-TC-542 | KAN-41 EC-2 | data: unknown_type
    """
    board = agency_notice_board

    with allure.step(f"Open the board with type={unknown_type_data.notice_type}"):
        board.open_with(unknown_type_data.notice_type)

    with allure.step("Verify the empty board"):
        expect(board.highlighted_pills).to_have_count(0)
        expect(board.notice_cards).to_have_count(0)
        expect(board.count_badge).to_have_text("0")
        expect(board.empty_state_text).to_have_text(NoticeBoardPage.NO_NOTICES)
