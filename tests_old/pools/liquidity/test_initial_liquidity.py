import boa
import pytest

from tests.fixtures.accounts import add_base_pool_liquidity, mint_account
from tests.utils.tokens import mint_for_testing


@pytest.fixture()
def initial_setup_alice(
    alice,
    deposit_amounts,
    swap,
    pool_type,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
    base_pool_lp_token,
    initial_balance,
    initial_amounts,
    pool_tokens,
    underlying_tokens,
):
    mint_for_testing(alice, 1 * 10**18, None, True)

    if pool_type == 0:
        mint_account(alice, pool_tokens, initial_balance, initial_amounts)
        with boa.env.prank(alice):
            for token in pool_tokens:
                token.approve(swap.address, 2**256 - 1)

    else:
        add_base_pool_liquidity(alice, base_pool, base_pool_tokens, base_pool_decimals)
        mint_for_testing(alice, initial_amounts[0], underlying_tokens[0], False)

        with boa.env.prank(alice):
            for token in underlying_tokens:
                token.approve(swap.address, 2**256 - 1)


@pytest.mark.parametrize("min_amount", [0, 10**18])
def test_initial(
    alice,
    initial_setup_alice,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    pool_token_types,
    metapool_token_type,
    min_amount,
    decimals,
    meta_decimals,
    deposit_amounts,
    initial_amounts,
):
    swap.add_liquidity(deposit_amounts, len(pool_tokens) * min_amount, sender=alice)

    token_types = pool_token_types if pool_type == 0 else [metapool_token_type, 18]

    for coin, und_coin, amount, initial, pool_token_type in zip(
        pool_tokens, underlying_tokens, deposit_amounts, initial_amounts, token_types
    ):
        if pool_type == 0:
            assert coin.balanceOf(alice) == pytest.approx(initial - amount, rel=1.5e-2)
            assert coin.balanceOf(swap) == pytest.approx(amount, rel=1.5e-2)
        else:
            assert und_coin.balanceOf(alice) == pytest.approx(initial - amount, rel=1.5e-2)
            assert und_coin.balanceOf(swap) == pytest.approx(amount, rel=1.5e-2)
