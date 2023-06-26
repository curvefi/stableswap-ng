import boa
import pytest

from tests.utils.tokens import mint_for_testing


@pytest.mark.parametrize("min_amount", [0, 10**18])
def test_initial(alice, swap_plain, coins, decimals, min_amount, initial_amounts):

    amounts = [10**d for d in decimals]
    for idx in range(2):
        mint_for_testing(coins[idx], alice, amounts[idx], mint_eth=False)

    with boa.env.prank(alice):
        swap_plain.add_liquidity(
            amounts,
            min_amount,
        )

    for coin, amount, initial in zip(coins, amounts, initial_amounts):

        assert coin.balanceOf(alice) == initial - amount
        assert coin.balanceOf(swap_plain) == amount


@pytest.mark.parametrize("idx", range(2))
def test_initial_liquidity_missing_coin(alice, swap_plain, idx, decimals):
    amounts = [10**i for i in decimals]
    amounts[idx] = 0
    with boa.reverts(), boa.env.prank(alice):
        swap_plain.add_liquidity(amounts, 0)
