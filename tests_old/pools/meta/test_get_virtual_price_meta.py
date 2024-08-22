import itertools

import pytest

pytestmark = pytest.mark.usefixtures("meta_setup")


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
def test_exchange_underlying(bob, meta_swap, sending, receiving, meta_decimals, base_pool_decimals, underlying_tokens):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    virtual_price = meta_swap.get_virtual_price()

    amount = 10 ** underlying_decimals[sending]
    if sending > 0:
        underlying_tokens[sending + 1]._mint_for_testing(bob, amount)

    meta_swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

    assert meta_swap.get_virtual_price() > virtual_price
