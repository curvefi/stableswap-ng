import pytest

pytestmark = pytest.mark.usefixtures("meta_setup")


def test_exchange_underlying(
    bob, charlie, meta_swap, underlying_tokens, meta_decimals, base_pool_decimals, metapool_token_type
):
    initial_amount = underlying_tokens[0].balanceOf(bob)

    amount = 10 ** base_pool_decimals[0]
    underlying_tokens[2]._mint_for_testing(bob, amount)

    meta_swap.exchange_underlying(1, 0, amount, 0, charlie, sender=bob)
    assert underlying_tokens[0].balanceOf(charlie) > 0
    if metapool_token_type == 2:
        # multiple transfers trigger multiple rebases
        delta_rebasing = 5 * 10 ** base_pool_decimals[0]
        underlying_tokens[0].balanceOf(bob) == pytest.approx(initial_amount, abs=delta_rebasing)
    else:
        assert underlying_tokens[0].balanceOf(bob) == initial_amount
