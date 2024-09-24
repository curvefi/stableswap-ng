import boa
import pytest

from tests.constants import POOL_TYPES, TOKEN_TYPES
from tests.fixtures.accounts import add_base_pool_liquidity, mint_account
from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils.tokens import mint_for_testing

DEPOSIT_AMOUNT = INITIAL_AMOUNT // 100
pytestmark = pytest.mark.only_oracle_tokens


@pytest.fixture()
def initial_setup_alice(pool_type, request):
    """
    Set up the initial state for Alice.
    Run either the basic or meta fixture depending on the pool type.
    """
    fixtures = {POOL_TYPES["basic"]: "basic_setup_alice", POOL_TYPES["meta"]: "meta_setup_alice"}
    return request.getfixturevalue(fixtures[pool_type])


@pytest.fixture()
def basic_setup_alice(
    alice,
    basic_initial_amounts,
    initial_balance,
    oracle_tokens,
    basic_swap,
    base_pool_tokens,
    base_pool,
    base_pool_decimals,
    underlying_tokens,
):
    mint_for_testing(alice, amount=1 * 10**18, token_contract=None, mint_eth=True)
    mint_account(alice, oracle_tokens, initial_balance, basic_initial_amounts)
    with boa.env.prank(alice):
        for token in oracle_tokens:
            token.approve(basic_swap.address, 2**256 - 1)


@pytest.fixture()
def meta_setup_alice(
    alice,
    base_pool_tokens,
    base_pool,
    base_pool_decimals,
    meta_initial_amounts,
    meta_swap,
    underlying_tokens,
):
    mint_for_testing(alice, amount=1 * 10**18, token_contract=None, mint_eth=True)
    add_base_pool_liquidity(alice, base_pool, base_pool_tokens, base_pool_decimals)
    mint_for_testing(alice, meta_initial_amounts[0], underlying_tokens[0], False)
    with boa.env.prank(alice):
        for token in underlying_tokens:
            token.approve(meta_swap.address, 2**256 - 1)


def test_initial_liquidity(
    alice,
    initial_setup_alice,
    swap,
    pool_type,
    pool_token_types,
    metapool_token_type,
    decimals,
    meta_decimals,
    oracle_tokens,
    metapool_token,
):
    if pool_type == 0:
        amounts = [
            (
                DEPOSIT_AMOUNT * 10 ** decimals[i] * 10**18 // oracle_tokens[i].exchangeRate()
                if t == TOKEN_TYPES["oracle"]
                else DEPOSIT_AMOUNT * 10 ** decimals[i]
            )
            for i, t in enumerate(pool_token_types)
        ]
    else:
        amounts = (
            [
                DEPOSIT_AMOUNT * 10**meta_decimals * 10**18 // metapool_token.exchangeRate(),
                DEPOSIT_AMOUNT * 10**18,
            ]
            if metapool_token_type == 1
            else [DEPOSIT_AMOUNT * 10**meta_decimals, DEPOSIT_AMOUNT * 10**18]
        )

    swap.add_liquidity(amounts, 0, sender=alice)
    swap.add_liquidity(amounts, 0, sender=alice)

    assert swap.admin_balances(0) == 0
    assert swap.admin_balances(1) == 0


def test_oracles(alice, swap, pool_size, pool_type):
    if pool_type == POOL_TYPES["basic"]:
        assert swap._immutables.rate_oracles != [0] * pool_size
    else:
        assert swap._immutables.rate_oracle


def test_get_dy_basic(
    alice,
    basic_setup_alice,
    basic_swap,
    pool_token_types,
    decimals,
    meta_decimals,
    oracle_tokens,
    metapool_token,
):
    amounts = [
        (
            DEPOSIT_AMOUNT * 10 ** decimals[i] * 10**18 // oracle_tokens[i].exchangeRate()
            if t == 1
            else DEPOSIT_AMOUNT * 10 ** decimals[i]
        )
        for i, t in enumerate(pool_token_types)
    ]

    basic_swap.add_liquidity(amounts, 0, sender=alice)

    rate_1 = 10**18 if pool_token_types[0] != 1 else oracle_tokens[0].exchangeRate()
    rate_2 = 10**18 if pool_token_types[1] != 1 else oracle_tokens[1].exchangeRate()

    assert basic_swap.get_dy(0, 1, rate_2) == pytest.approx(rate_1, rel=1e-3)


def test_get_dy_meta(
    alice,
    meta_setup_alice,
    meta_swap,
    metapool_token_type,
    decimals,
    meta_decimals,
    oracle_tokens,
    metapool_token,
):
    amounts = (
        [
            DEPOSIT_AMOUNT * 10**meta_decimals * 10**18 // metapool_token.exchangeRate(),
            DEPOSIT_AMOUNT * 10**18,
        ]
        if metapool_token_type == 1
        else [DEPOSIT_AMOUNT * 10**meta_decimals, DEPOSIT_AMOUNT * 10**18]
    )

    meta_swap.add_liquidity(amounts, 0, sender=alice)

    rate_1 = 1 if metapool_token_type != 1 else metapool_token.exchangeRate()

    assert meta_swap.get_dy(0, 1, 10**18) == pytest.approx(rate_1, rel=1e-3)
