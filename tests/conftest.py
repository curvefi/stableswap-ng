import itertools
import os

import boa
import pytest

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


def pytest_addoption(parser):
    parser.addoption(
        "--pool-size",
        action="store",
        default="2",
        help="pool size to test against",
    )
    parser.addoption(
        "--pool-types",
        action="store",
        default="basic,meta",
        help="pool type to test against",
    )
    parser.addoption(
        "--token-types",
        action="store",
        default="plain,oracle,rebasing",
        help="comma-separated list of ERC20 token types to test against",
    )
    parser.addoption(
        "--decimals",
        action="store",
        default="18,18",
        help="comma-separated list of ERC20 token precisions to test against",
    )
    parser.addoption(
        "--return-type",
        action="store",
        default="revert,False,None",
        help="comma-separated list of ERC20 token return types to test against",
    )


def pytest_generate_tests(metafunc):
    pool_size = int(metafunc.config.getoption("pool_size"))

    if "pool_size" in metafunc.fixturenames:
        metafunc.parametrize(
            "pool_size",
            [pool_size],
            indirect=True,
            ids=[f"(PoolSize={pool_size})"],
        )

    if "pool_type" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("pool_types").split(",")
        metafunc.parametrize(
            "pool_type",
            [pool_types[pool_type] for pool_type in cli_options],
            indirect=True,
            ids=[f"(PoolType={pool_type})" for pool_type in cli_options],
        )

    if "pool_token_types" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("token_types").split(",")
        if "eth" in cli_options:
            cli_options.remove("eth")
            cli_options = ["eth"] + cli_options

        combinations = list(itertools.combinations_with_replacement(cli_options, pool_size))

        metafunc.parametrize(
            "pool_token_types",
            [[token_types[idx] for idx in c] for c in combinations],
            indirect=True,
            ids=[f"(PoolTokenTypes={c})" for c in combinations],
        )

    if "metapool_token_type" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("token_types").split(",")

        # for meta pool only 1st coin is selected
        metafunc.parametrize(
            "metapool_token_type",
            [token_types[c] for c in cli_options],
            indirect=True,
            ids=[f"(MetaTokenType={c})" for c in cli_options],
        )

    if "initial_decimals" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("decimals")
        metafunc.parametrize(
            "initial_decimals",
            [[int(i) for i in cli_options.split(",")]],
            indirect=True,
            ids=[f"(Decimals={cli_options})"],
        )

    if "return_type" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("return_type").split(",")
        return_type_ids = [return_types[v] for v in cli_options]

        metafunc.parametrize(
            "return_type",
            return_type_ids,
            indirect=True,
            ids=[f"(ReturnType={i})" for i in cli_options],
        )


@pytest.fixture(scope="session")
def pool_size(request):
    return request.param


@pytest.fixture(scope="session")
def pool_type(request):
    return request.param


@pytest.fixture(scope="session")
def pool_token_types(request):
    return request.param


@pytest.fixture(scope="session")
def metapool_token_type(request):
    return request.param


@pytest.fixture(scope="session")
def return_type(request):
    return request.param


@pytest.fixture(scope="session")
def initial_decimals(request):
    return request.param


@pytest.fixture(scope="session")
def decimals(initial_decimals, pool_token_types):
    # oracle tokens are always 18 decimals
    return [d if t != 1 else 18 for d, t in zip(initial_decimals, pool_token_types)]


@pytest.fixture(scope="session")
def meta_decimals(initial_decimals, metapool_token_type, decimals):
    # oracle tokens are always 18 decimals
    return decimals[0] if metapool_token_type != 1 else 18


# Usage
# @pytest.mark.only_for_token_types(1,2)
#
# will not be skipped only if at least one of tokens in pool is eth or oracle
# can be applied to classes
#
# @pytest.mark.only_for_token_types(2)
# class TestPoolsWithOracleToken:
@pytest.fixture(autouse=True)
def skip_by_token_type(request, swap):
    only_for_token_types = request.node.get_closest_marker("only_for_token_types")
    if only_for_token_types:
        asset_types = swap._immutables.asset_types
        if not any(asset_type in only_for_token_types.args for asset_type in asset_types):
            pytest.skip("skipped because no tokens for these types")


@pytest.fixture(autouse=True)
def skip_rebasing(request, swap):
    only_for_token_types = request.node.get_closest_marker("skip_rebasing_tokens")
    if only_for_token_types:
        asset_types_contains_rebasing = 2 in swap._immutables.asset_types
        if asset_types_contains_rebasing:
            pytest.skip("skipped because test excludes rebasing tokens")


@pytest.fixture(autouse=True)
def skip_oracle(request, swap):
    only_for_token_types = request.node.get_closest_marker("skip_oracle_tokens")
    if only_for_token_types:
        asset_types_contains_oracle = 1 in swap._immutables.asset_types
        if asset_types_contains_oracle:
            pytest.skip("skipped because test excludes oraclised tokens")


@pytest.fixture(autouse=True)
def only_oracle(request, swap):
    only_for_token_types = request.node.get_closest_marker("only_oracle_tokens")
    if only_for_token_types:
        asset_types_contains_rebasing = 1 in swap._immutables.asset_types
        if not asset_types_contains_rebasing:
            pytest.skip("skipped because test excludes oraclised tokens")


# Usage
# @pytest.mark.only_for_pool_type(1)
# class TestMetaPool...
@pytest.fixture(autouse=True)
def skip_by_pool_type(request, pool_type):
    only_for_pool_type = request.node.get_closest_marker("only_for_pool_type")
    if only_for_pool_type:
        if pool_type not in only_for_pool_type.args:
            pytest.skip("skipped because another pool type")


@pytest.fixture(scope="session")
def forked_chain():
    rpc_url = os.getenv("WEB3_PROVIDER_URL")
    assert rpc_url is not None, "Provider url is not set, add WEB3_PROVIDER_URL param to env"
    boa.env.fork(url=rpc_url)
