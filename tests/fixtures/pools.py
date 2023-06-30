import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

# TODO: meta pool


@pytest.fixture(scope="module")
def swap(
    owner,
    mint_owner,
    factory,
    weth,
    pool_token_types,
    pool_tokens,
    amm_interface_plain,
    amm_implementation_plain,
    set_plain_implementations,
    zero_address,
):
    oracle_method_id = function_signature_to_4byte_selector("exchangeRate()")

    A = 2000
    fee = 1000000
    method_ids = [bytes(b"")] * 8
    oracles = [zero_address] * 8
    asset_type = 0  # 0 = USD, 1 = ETH, 2 = BTC, 3 = Other
    is_rebasing = [False] * 8

    for i, t in enumerate(pool_token_types):
        if t == 0:
            A = 2000
            fee = 1000000
            asset_type = 0
        elif t == 1:
            A = 1000
            fee = 3000000
            asset_type = 1
        elif t == 2:
            A = 1000
            fee = 3000000
            asset_type = 1
            method_ids[i] = oracle_method_id
            oracles[i] = pool_tokens[i].address
        elif t == 3:
            A = 500
            fee = 4000000
            asset_type = 1
            is_rebasing[i] = True

    with boa.env.prank(owner):
        pool = factory.deploy_plain_pool(
            "test",
            "test",
            [pool_tokens[0].address, pool_tokens[1].address, *[zero_address] * 6],
            A,
            fee,
            866,
            method_ids,
            oracles,
            asset_type,
            0,
            is_rebasing,
        )

    return amm_interface_plain.at(pool)


# <---------------------   Functions   --------------------->
# TODO: add Factory Meta Implementation
@pytest.fixture(scope="module")
def add_initial_liquidity(owner, approve_owner, mint_owner, deposit_amounts, swap):
    with boa.env.prank(owner):
        swap.add_liquidity(deposit_amounts, 0)


@pytest.fixture(scope="module")
def add_initial_liquidity_alice(alice, approve_alice, mint_alice, deposit_amounts, swap):
    with boa.env.prank(alice):
        swap.add_liquidity(deposit_amounts, 0)
