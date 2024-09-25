import math

import boa
import pytest
from eth_account.account import Account, LocalAccount

from tests.constants import POOL_TYPES
from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils.tokens import mint_for_testing


@pytest.fixture()
def deployer():
    return boa.env.generate_address()


@pytest.fixture()
def owner():
    return boa.env.generate_address()


@pytest.fixture()
def fee_receiver():
    return boa.env.generate_address()


@pytest.fixture()
def eth_acc() -> LocalAccount:
    return Account.create()


@pytest.fixture()
def alice():
    return boa.env.generate_address()


@pytest.fixture()
def bob():
    return boa.env.generate_address()


@pytest.fixture()
def charlie():
    return boa.env.generate_address()


@pytest.fixture()
def dave():
    return boa.env.generate_address()


@pytest.fixture()
def erin():
    return boa.env.generate_address()


@pytest.fixture()
def frank():
    return boa.env.generate_address()


@pytest.fixture()
def accounts(bob, charlie, dave, erin, frank):
    return [bob, charlie, dave, erin, frank]


# <---------------------   Functions   --------------------->
def mint_account(account, pool_tokens, initial_balance, initial_amounts):
    mint_for_testing(account, initial_balance, token_contract=None, mint_eth=True)
    for pool_token, amount in zip(pool_tokens, initial_amounts):
        mint_for_testing(account, amount, pool_token, mint_eth=False)


def approve_account(account, pool_tokens, swap):
    for pool_token in pool_tokens:
        with boa.env.prank(account):
            pool_token.approve(swap.address, 2**256 - 1)


# <---------------------   Functions   --------------------->
def add_base_pool_liquidity(user, base_pool, base_pool_tokens, base_pool_decimals):
    amount = INITIAL_AMOUNT // 3
    with boa.env.prank(user):
        for d, token in zip(base_pool_decimals, base_pool_tokens):
            token._mint_for_testing(user, amount * 10**d)
            token.approve(base_pool.address, 2**256 - 1)

        amounts = [amount * 10**d for d in base_pool_decimals]
        base_pool.add_liquidity(amounts, 0)


@pytest.fixture()
def add_initial_liquidity_owner_basic(
    owner,
    deposit_amounts,
    basic_swap,
    underlying_tokens,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
    base_pool_lp_token,
    pool_tokens,
    initial_balance,
    basic_initial_amounts,
):
    mint_account(owner, pool_tokens, initial_balance, basic_initial_amounts)
    approve_account(owner, pool_tokens, basic_swap)
    with boa.env.prank(owner):
        basic_swap.add_liquidity(deposit_amounts, 0)


@pytest.fixture()
def add_initial_liquidity_owner_meta(
    owner,
    deposit_meta_amounts,
    meta_swap,
    metapool_token,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
    base_pool_lp_token,
    pool_tokens,
    initial_balance,
    meta_initial_amounts,
):
    mint_account(owner, pool_tokens, initial_balance, meta_initial_amounts)
    approve_account(owner, pool_tokens, meta_swap)
    add_base_pool_liquidity(owner, base_pool, base_pool_tokens, base_pool_decimals)
    with boa.env.prank(owner):
        base_pool_lp_token.approve(meta_swap.address, 2**256 - 1)
        lp_token_bal = base_pool_lp_token.balanceOf(owner)
        to_mint_token0 = lp_token_bal * 10 ** metapool_token.decimals() // 10 ** base_pool_lp_token.decimals()

        mint_for_testing(owner, to_mint_token0, metapool_token, False)
        metapool_token.approve(meta_swap.address, 2**256 - 1)

        meta_swap.add_liquidity([to_mint_token0, lp_token_bal], 0)


@pytest.fixture()
def add_initial_liquidity_owner(pool_type, request):
    fixture_name = {
        POOL_TYPES["basic"]: "add_initial_liquidity_owner_basic",
        POOL_TYPES["meta"]: "add_initial_liquidity_owner_meta",
    }[pool_type]
    return request.getfixturevalue(fixture_name)


@pytest.fixture()
def approve_meta_bob(bob, underlying_tokens, swap):
    with boa.env.prank(bob):
        for token in underlying_tokens:
            token.approve(swap.address, 2**256 - 1)


@pytest.fixture()
def basic_setup(
    alice,
    bob,
    deposit_basic_amounts,
    basic_swap,
    initial_balance,
    basic_initial_amounts,
    pool_tokens,
    metapool_token_type,
):
    # assert metapool_token_type is not None, "Fixture required downstream"
    # bob and alice have tokens from pool
    for user in [alice, bob]:
        mint_account(user, pool_tokens, initial_balance, basic_initial_amounts)
        approve_account(user, pool_tokens, basic_swap)
    # alice adds liquidity to the pool, bob holds tokens for tests
    with boa.env.prank(alice):
        basic_swap.add_liquidity(deposit_basic_amounts, 0)

    # mint_account(bob, pool_tokens, initial_balance, basic_initial_amounts)
    # approve_account(bob, pool_tokens, basic_swap)
    # @dev small cleanup, code was not consistent
    # mint_for_testing(bob, 1 * 10**18, None, True)
    # with boa.env.prank(bob):
    #     for token in pool_tokens:
    #         token.approve(basic_swap.address, 2**256 - 1)


@pytest.fixture()
def meta_setup(
    alice,
    bob,
    deposit_meta_amounts,
    meta_swap,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
    base_pool_lp_token,
    initial_balance,
    meta_initial_amounts,
    underlying_tokens,
    pool_tokens,
    # add_initial_liquidity_owner_meta,  # - this fixture leads to doubled liquidity in metapool,
    # results in failing some tests
    metapool_token,
):
    approve_account(alice, pool_tokens, meta_swap)
    mint_account(alice, pool_tokens, initial_balance, meta_initial_amounts)
    mint_for_testing(bob, 1 * 10**18, None, True)

    add_base_pool_liquidity(alice, base_pool, base_pool_tokens, base_pool_decimals)
    alice_bp_balance_norm = base_pool_lp_token.balanceOf(alice) / 10**18
    alice_mp_balance_norm = metapool_token.balanceOf(alice) / 10 ** metapool_token.decimals()

    if alice_mp_balance_norm < alice_bp_balance_norm:
        mint_for_testing(alice, int(math.ceil(alice_bp_balance_norm) * 10 ** metapool_token.decimals()), metapool_token)

    with boa.env.prank(alice):
        metapool_token.approve(meta_swap.address, 2**256 - 1)
        base_pool_lp_token.approve(meta_swap.address, 2**256 - 1)
        meta_swap.add_liquidity(deposit_meta_amounts, 0)

    add_base_pool_liquidity(bob, base_pool, base_pool_tokens, base_pool_decimals)
    mint_for_testing(bob, initial_balance, metapool_token, False)
    assert metapool_token.balanceOf(bob) == pytest.approx(base_pool_lp_token.balanceOf(bob))

    with boa.env.prank(bob):
        for underlying_token in underlying_tokens:
            underlying_token.approve(meta_swap.address, 2**256 - 1)


@pytest.fixture()
def initial_setup(pool_type, request, metapool_token_type, pool_token_types, initial_decimals):
    """
    Set up the initial state for a pool test.
    Run either basic_setup or meta_setup depending on the pool_type.
    """
    if pool_type == POOL_TYPES["meta"]:
        assert metapool_token_type is not None, "metapool_token_type is required for meta pools"
    else:
        # For basic pools, we don't care about metapool_token_type
        metapool_token_type = None
    # Continue with the general logic
    assert all(fixture is not None for fixture in (initial_decimals, pool_token_types)), "Fixtures required downstream"
    fixture_name = {POOL_TYPES["basic"]: "basic_setup", POOL_TYPES["meta"]: "meta_setup"}[pool_type]
    return request.getfixturevalue(fixture_name)
