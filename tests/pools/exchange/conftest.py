import pytest

from tests.constants import TOKEN_TYPES
from tests.utils import get_asset_types_in_pool


@pytest.fixture()
def contains_rebasing_tokens(swap):
    if TOKEN_TYPES["rebasing"] not in get_asset_types_in_pool(swap):
        return True
    return False


@pytest.fixture()
def check_rebasing(swap, pool_token_types, pool_type, metapool_token_type):
    a = swap._immutables.pool_contains_rebasing_tokens
    b = (pool_type == 0 and (pool_token_types[0] == 2 or pool_token_types[1] == 2)) or (
        pool_type == 1 and metapool_token_type == 2
    )
    assert a == b


@pytest.fixture()
def has_rebasing_tokens(swap):
    if TOKEN_TYPES["rebasing"] in get_asset_types_in_pool(swap):
        return True
    return False
