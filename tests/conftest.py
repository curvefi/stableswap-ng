import itertools
import os

import boa
import pytest

from tests.utils import get_asset_types_in_pool

pytest_plugins = [
    "tests.fixtures.accounts",
    "tests.fixtures.constants",
    "tests.fixtures.factory",
    "tests.fixtures.mocks",
    "tests.fixtures.pools",
    "tests.fixtures.tokens",
]

pool_types = {"basic": 0, "meta": 1}
token_types = {"plain": 0, "oracle": 1, "rebasing": 2}
return_types = {"revert": 0, "False": 1, "None": 2}
decimal_types = [(18, 18), (10, 12)]


def pytest_generate_tests(metafunc):
    if "pool_type" in metafunc.fixturenames:
        pool_type_items = sorted(pool_types.items())
        metafunc.parametrize(
            "pool_type",
            [v for k, v in pool_type_items],
            ids=[f"(PoolType={k})" for k, v in pool_type_items],
            indirect=True,  # to declare the fixture scope
        )

    if "pool_token_types" in metafunc.fixturenames:
        combinations = sorted(itertools.combinations_with_replacement(token_types.items(), 2))
        metafunc.parametrize(
            "pool_token_types",
            [(v1, v2) for (k1, v1), (k2, v2) in combinations],
            ids=[f"(PoolTokenTypes={k1}+{k2})" for (k1, v1), (k2, v2) in combinations],
            indirect=True,  # to declare the fixture scope
        )

    if "metapool_token_type" in metafunc.fixturenames:
        # for meta pool only 1st coin is selected
        token_type_items = sorted(token_types.items())
        metafunc.parametrize(
            "metapool_token_type",
            [v for k, v in token_type_items],
            ids=[f"(MetaTokenType={k})" for k, v in token_type_items],
            indirect=True,  # to declare the fixture scope
        )

    if "initial_decimals" in metafunc.fixturenames:
        metafunc.parametrize(
            "initial_decimals",
            decimal_types,
            ids=[f"(Decimals={i},{j})" for i, j in decimal_types],
            indirect=True,  # to declare the fixture scope
        )


@pytest.fixture(scope="session")
def pool_size():
    return 2


@pytest.fixture(scope="session")
def pool_type(request):  # to declare the fixture scope
    return request.param


@pytest.fixture(scope="session")
def pool_token_types(request):  # to declare the fixture scope
    return request.param


@pytest.fixture(scope="session")
def metapool_token_type(request):  # to declare the fixture scope
    return request.param


@pytest.fixture(scope="session")
def initial_decimals(request):  # to declare the fixture scope
    return request.param


@pytest.fixture(scope="session")
def decimals(initial_decimals, pool_token_types):
    return [
        # oracle tokens are always 18 decimals
        18 if token_type == 1 else decimals
        for decimals, token_type in zip(initial_decimals, pool_token_types)
    ]


@pytest.fixture(scope="session")
def meta_decimals(metapool_token_type, decimals):
    # oracle tokens are always 18 decimals
    return 18 if metapool_token_type == 1 else decimals[0]


# Usage
# @pytest.mark.only_for_token_types(1,2)
#
# will not be skipped only if at least one of tokens in pool is eth or oracle
# can be applied to classes
#
# @pytest.mark.only_for_token_types(2)
# class TestPoolsWithOracleToken:
@pytest.fixture(autouse=True)
def skip_by_token_type(request, pool_tokens):
    only_for_token_types = request.node.get_closest_marker("only_for_token_types")
    if only_for_token_types:
        asset_types = [tkn.asset_type() for tkn in pool_tokens]
        if not any(asset_type in only_for_token_types.args for asset_type in asset_types):
            pytest.skip("skipped because no tokens for these types")


@pytest.fixture(autouse=True)
def skip_rebasing(request, swap):
    only_for_token_types = request.node.get_closest_marker("skip_rebasing_tokens")
    if only_for_token_types:
        if 2 in get_asset_types_in_pool(swap):
            pytest.skip("skipped because test includes rebasing tokens")


@pytest.fixture(autouse=True)
def skip_oracle(request, pool_tokens):
    only_for_token_types = request.node.get_closest_marker("skip_oracle_tokens")
    if only_for_token_types:
        asset_types = [tkn.asset_type() for tkn in pool_tokens]
        asset_types_contains_oracle = 1 in asset_types
        if asset_types_contains_oracle:
            pytest.skip("skipped because test includes oraclised tokens")


@pytest.fixture(autouse=True)
def only_oracle(request, pool_tokens):
    only_for_token_types = request.node.get_closest_marker("only_oracle_tokens")
    if only_for_token_types:
        asset_types = [tkn.asset_type() for tkn in pool_tokens]
        asset_types_contains_rebasing = 1 in asset_types
        if not asset_types_contains_rebasing:
            pytest.skip("skipped because test excludes oraclised tokens")


@pytest.fixture(autouse=True)
def only_rebasing(request, swap):
    marker = request.node.get_closest_marker("contains_rebasing_tokens")
    if marker:
        asset_types_contains_rebasing = 2 in get_asset_types_in_pool(swap)
        if not asset_types_contains_rebasing:
            pytest.skip("skipped because test excludes rebasing tokens")


# Usage
# @pytest.mark.only_for_pool_type(1)
# class TestMetaPool...
@pytest.fixture(autouse=True)
def skip_by_pool_type(request, pool_type):
    only_for_pool_type = request.node.get_closest_marker("only_for_pool_type")
    if only_for_pool_type:
        if pool_type not in only_for_pool_type.args:
            pytest.skip("skipped because another pool type")


@pytest.fixture(scope="module")
def forked_chain():
    rpc_url = os.getenv("WEB3_PROVIDER_URL")
    assert rpc_url is not None, "Provider url is not set, add WEB3_PROVIDER_URL param to env"
    boa.env.fork(url=rpc_url)
