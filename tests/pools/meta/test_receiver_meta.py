import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


def test_exchange_underlying(alice, charlie, swap, underlying_tokens, meta_decimals, base_pool_decimals):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount = 10 ** underlying_decimals[1]
    underlying_tokens[1]._mint_for_testing(alice, amount, sender=alice)

    swap.exchange_underlying(1, 0, amount, 0, charlie, sender=alice)
    assert underlying_tokens[0].balanceOf(charlie) > 0
    assert underlying_tokens[0].balanceOf(alice) == 0
