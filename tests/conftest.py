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
        help="comma-separated list of plain pool sizes to test against",
    )
    # TODO: add meta implementation
    parser.addoption(
        "--pool-type",
        action="store",
        default="basic",
        help="comma-separated list of pool types to test against",
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
    if "pool_size" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("pool_size").split(",")
        pool_sizes = [int(v) for v in cli_options]

        # TODO: remove after adding implementations
        assert pool_sizes == [2], "Only 2-coin pools supported"

        metafunc.parametrize(
            "pool_size",
            pool_sizes,
            indirect=True,
            ids=[f"(PoolSize={i})" for i in cli_options],
        )

    if "pool_type" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("pool_type").split(",")
        pool_type_ids = [pool_types[v] for v in cli_options]
        metafunc.parametrize(
            "pool_type",
            pool_type_ids,
            indirect=True,
            ids=[f"(PoolType={i})" for i in cli_options],
        )

    if "pool_token_types" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("token_types").split(",")

        # TODO: only 2-coin pools are supported
        combs = list(combinations(cli_options, 2))
        # do not include (eth,eth) pair
        for t in cli_options:
            if t != "eth":
                combs.append((t, t))

        metafunc.parametrize(
            "pool_token_types",
            [(token_types[v[0]], token_types[v[1]]) for v in combs],
            indirect=True,
            ids=[f"(PoolTokenTypes={c})" for c in combs],
        )

    if "decimals" in metafunc.fixturenames:
        cli_options = metafunc.config.getoption("decimals")
        metafunc.parametrize(
            "decimals",
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
def decimals(request):
    return request.param


@pytest.fixture(scope="module")
def forked_chain():
    rpc_url = os.getenv("WEB3_PROVIDER_URL")
    assert rpc_url is not None, "Provider url is not set, add WEB3_PROVIDER_URL param to env"
    boa.env.fork(url=rpc_url)
