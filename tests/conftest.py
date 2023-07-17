import os
from itertools import combinations

import boa
import pytest

pytest_plugins = [
    "tests.fixtures.accounts",
    "tests.fixtures.constants",
    "tests.fixtures.factory",
    "tests.fixtures.pools",
    "tests.fixtures.tokens",
]

pool_types = {"basic": 0, "meta": 1}
token_types = {"plain": 0, "eth": 1, "oracle": 2, "rebasing": 3}
return_types = {"revert": 0, "False": 1, "None": 2}


def pytest_addoption(parser):
    parser.addoption(
        "--pool-size",
        action="store",
        default="2",
        help="pool size to test against",
    )
    parser.addoption(
        "--pool-type",
        action="store",
        default="basic",
        help="pool type to test against",
    )
    parser.addoption(
        "--token-types",
        action="store",
        default="plain,eth,oracle,rebasing",
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

    # TODO: remove after adding implementations
    # assert pool_size == 2, "Only 2-coin pools supported"

    if "pool_size" in metafunc.fixturenames:
        metafunc.parametrize(
            "pool_size",
            [pool_size],
            indirect=True,
            ids=[f"(PoolSize={pool_size})"],
        )

    pool_type = metafunc.config.getoption("pool_type")

    if "pool_type" in metafunc.fixturenames:
        metafunc.parametrize(
            "pool_type",
            [pool_types[pool_type]],
            indirect=True,
            ids=[f"(PoolType={pool_type})"],
        )

    if "pool_token_types" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("token_types").split(",")
        if "eth" in cli_options:
            cli_options.remove("eth")
            cli_options = ["eth"] + cli_options

        if pool_types[pool_type] == 0:
            combs = list(combinations(cli_options, pool_size))
            if pool_size == 2:
                # do not include (eth,eth) pair
                for t in cli_options:
                    if t != "eth":
                        combs.append((t, t))

            metafunc.parametrize(
                "pool_token_types",
                [(token_types[c[0]], token_types[c[1]]) for c in combs],
                indirect=True,
                ids=[f"(PoolTokenTypes={c})" for c in combs],
            )
        else:
            # workaround for generating tokens
            # for meta pool only 1st coin is selected
            metafunc.parametrize(
                "pool_token_types",
                [[token_types[c]] for c in cli_options],
                indirect=True,
                ids=[f"(PoolTokenTypes={c})" for c in cli_options],
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
def return_type(request):
    return request.param


@pytest.fixture(scope="session")
def initial_decimals(request):
    return request.param


@pytest.fixture(scope="session")
def decimals(initial_decimals, pool_token_types):
    # eth and oracle tokens are always 18 decimals
    return [d if t in [0, 3] else 18 for d, t in zip(initial_decimals, pool_token_types)]


# Usage
# @pytest.mark.only_for_token_types(1,2)
#
# will not be skipped only if at least one of tokens in pool is eth or oracle
# can be applied to classes
#
# @pytest.mark.only_for_token_types(2)
# class TestPoolsWithOracleToken:
@pytest.fixture(autouse=True)
def skip_by_token_type(request, pool_token_types):
    only_for_token_types = request.node.get_closest_marker("only_for_token_types")
    if only_for_token_types:
        if not any(pool_token_type in only_for_token_types.args for pool_token_type in pool_token_types):
            pytest.skip("skipped because no tokens for these types")


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
