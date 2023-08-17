import itertools

import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
def test_exchange_underlying(bob, swap, sending, receiving, meta_decimals, base_pool_decimals):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    virtual_price = swap.get_virtual_price()

    amount = 10 ** underlying_decimals[sending]
    swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

    assert swap.get_virtual_price() > virtual_price
