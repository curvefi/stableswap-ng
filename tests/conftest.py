import os
from itertools import combinations_with_replacement
from random import Random

import boa
import pytest

from tests.constants import DECIMAL_PAIRS, POOL_TYPES, TOKEN_TYPES

pytest_plugins = [
    "tests.fixtures.accounts",
    "tests.fixtures.constants",
    "tests.fixtures.contracts",
    "tests.fixtures.factory",
    "tests.fixtures.mocks",
    "tests.fixtures.pools",
    "tests.fixtures.tokens",
]


@pytest.fixture(scope="session", autouse=True)
def fast_mode():
    boa.env.enable_fast_mode()


def pytest_generate_tests(metafunc):
    if "pool_type" in metafunc.fixturenames:
        pool_type_items = sorted(POOL_TYPES.items())
        metafunc.parametrize(
            "pool_type", [v for k, v in pool_type_items], ids=[f"(PoolType={k})" for k, v in pool_type_items]
        )

    if "pool_token_types" in metafunc.fixturenames:
        pool_token_pairs = get_pool_token_pairs(metafunc)
        metafunc.parametrize(
            "pool_token_types",
            [(v1, v2) for (k1, v1), (k2, v2) in pool_token_pairs],
            ids=[f"(PoolTokenTypes={k1}+{k2})" for (k1, v1), (k2, v2) in pool_token_pairs],
        )

    if "metapool_token_type" in metafunc.fixturenames:
        # for meta pool only 1st coin is selected
        token_type_items = get_tokens_for_metafunc(metafunc)
        metafunc.parametrize(
            "metapool_token_type",
            [number for name, number in token_type_items],
            ids=[f"(MetaTokenType={name})" for name, number in token_type_items],
        )

    if "initial_decimals" in metafunc.fixturenames:
        # this is only used in the decimals fixture
        metafunc.parametrize("initial_decimals", DECIMAL_PAIRS, ids=[f"(Decimals={i},{j})" for i, j in DECIMAL_PAIRS])


def get_pool_token_pairs(metafunc):
    for name, number in TOKEN_TYPES.items():
        if metafunc.definition.get_closest_marker(f"only_{name}_tokens"):
            return [((name, number), (name, number))]

    items = get_tokens_for_metafunc(metafunc)
    # make all combinations possible
    all_combinations = list(combinations_with_replacement(items, 2))
    # make sure we get the same result in each worker
    random = Random(len(metafunc.fixturenames))
    # take 2 combinations for smaller test set
    return sorted(random.sample(all_combinations, k=2))


def get_tokens_for_metafunc(metafunc):
    return [
        (name, number)
        for name, number in TOKEN_TYPES.items()
        if not metafunc.definition.get_closest_marker(f"skip_{name}_tokens")
    ]


@pytest.fixture(scope="session")
def pool_size():
    return 2


@pytest.fixture()
def decimals(initial_decimals, pool_token_types):
    return [
        # oracle tokens are always 18 decimals
        18 if token_type == 1 else decimals
        for decimals, token_type in zip(initial_decimals, pool_token_types)
    ]


@pytest.fixture()
def meta_decimals(metapool_token_type, decimals):
    # oracle tokens are always 18 decimals
    return 18 if metapool_token_type == 1 else decimals[0]


@pytest.fixture(scope="module")
def forked_chain():
    rpc_url = os.getenv("WEB3_PROVIDER_URL")
    assert rpc_url is not None, "Provider url is not set, add WEB3_PROVIDER_URL param to env"
    boa.env.fork(url=rpc_url)
