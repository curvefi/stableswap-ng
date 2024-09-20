import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


def test_exchange_underlying(
    bob, charlie, swap, underlying_tokens, meta_decimals, base_pool_decimals
):
    initial_amount = underlying_tokens[0].balanceOf(bob)

    amount = 10 ** base_pool_decimals[0]
    underlying_tokens[2]._mint_for_testing(bob, amount)

    swap.exchange_underlying(1, 0, amount, 0, charlie, sender=bob)
    assert underlying_tokens[0].balanceOf(charlie) > 0
    assert underlying_tokens[0].balanceOf(bob) == initial_amount
