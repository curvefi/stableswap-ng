import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

# TODO: rebasing pool, pool with oracles, normal pool, pool with ETH

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture(scope="module")
def swap_plain(
    stableswap_factory,
    dai,
    usdc,
    bob,
    amm_implementation_plain,
):

    with boa.env.prank(bob):

        pool = stableswap_factory.deploy_plain_pool(
            "test",
            "test",
            [dai, usdc],
            2000,
            1000000,
            866,
            [b""] * 4,
            [ZERO_ADDRESS] * 4,
            0,
            0,
        )

    return amm_implementation_plain.at(pool)


@pytest.fixture(scope="module")
def swap_eth_rebasing(
    stableswap_factory,
    weth,
    steth,
    charlie,
    amm_implementation_plain,
):

    # TODO: make steth rebasing

    with boa.env.prank(charlie):

        pool = stableswap_factory.deploy_plain_pool(
            "test",
            "test",
            [weth, steth],
            1000,
            3000000,
            866,
            [b""] * 4,
            [ZERO_ADDRESS] * 4,
            0,
            0,
        )

    return amm_implementation_plain.at(pool)


@pytest.fixture(scope="module")
def swap_oracle(
    stableswap_factory,
    oracle_token_a,
    oracle_token_b,
    charlie,
    amm_implementation_plain,
):
    oracle_method_id = function_signature_to_4byte_selector("exchangeRate()")

    with boa.env.prank(charlie):

        pool = stableswap_factory.deploy_plain_pool(
            "test",
            "test",
            [oracle_token_a, oracle_token_b],
            500,
            4000000,
            866,
            [oracle_method_id, oracle_method_id, b"", b""],
            [ZERO_ADDRESS] * 4,
            0,
            0,
        )

    return amm_implementation_plain.at(pool)


@pytest.fixture(scope="module")
def swap_meta(
    stableswap_factory,
    dai,
    base_pool_token,  # TODO: implement base pool token
    charlie,
    amm_implementation_meta,
):
    # TODO: implement metapools
    pass
