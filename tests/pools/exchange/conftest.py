import pytest

from tests.constants import TOKEN_TYPES
from tests.utils import get_asset_types_in_pool


@pytest.fixture()
def contains_rebasing_tokens(swap):
    if TOKEN_TYPES["rebasing"] not in get_asset_types_in_pool(swap):
        pytest.skip("Test requires pools with no rebasing tokens")


@pytest.fixture()
def skip_rebasing_tokens(swap):
    if TOKEN_TYPES["rebasing"] in get_asset_types_in_pool(swap):
        pytest.skip("Test requires pools with rebasing tokens")
