import pytest

from fixtures.agency_home_fixtures import NO_SUBMITTED_AGENCY, _login_to_home, _submitted_agencies
from pages.notice_board_page import NoticeBoardPage
from test_data.notice_board_factory import NoticeBoardFactory, NoticeSearchData


def _open_as_agency(page) -> NoticeBoardPage:
    """Logs in as a submitted agency (the dev testing notice dismissed on Home) and opens the board."""
    for user in _submitted_agencies():
        if _login_to_home(page, user):
            board = NoticeBoardPage(page)
            board.open()
            return board
    pytest.skip(NO_SUBMITTED_AGENCY)


# ── Navigation fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def agency_notice_board(page) -> NoticeBoardPage:
    """The Notice Board, logged in as an agency whose application is submitted. The board is
    read-only, so any paid agency will do."""
    return _open_as_agency(page)


@pytest.fixture
def logged_out_notice_board(page):
    """Yields (board, titles) — the Notice Board opened logged out, and the notice titles an agency
    saw on it just before (logged in, then cookies cleared)."""
    titles = [card["title"] for card in _open_as_agency(page).read_cards()]
    page.context.clear_cookies()
    board = NoticeBoardPage(page)
    board.open()
    yield board, titles


# ── Data fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def title_word_data() -> NoticeSearchData:
    return NoticeBoardFactory.title_word()


@pytest.fixture
def title_word_in_capitals_data() -> NoticeSearchData:
    return NoticeBoardFactory.title_word_in_capitals()


@pytest.fixture
def body_only_word_data() -> NoticeSearchData:
    return NoticeBoardFactory.body_only_word()


@pytest.fixture
def word_within_alert_data() -> NoticeSearchData:
    return NoticeBoardFactory.word_within_alert()


@pytest.fixture
def no_match_data() -> NoticeSearchData:
    return NoticeBoardFactory.no_match()


@pytest.fixture
def html_tag_data() -> NoticeSearchData:
    return NoticeBoardFactory.html_tag()


@pytest.fixture
def over_max_length_data() -> NoticeSearchData:
    return NoticeBoardFactory.over_max_length()


@pytest.fixture
def unknown_type_data() -> NoticeSearchData:
    return NoticeBoardFactory.unknown_type()
