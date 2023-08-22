import itertools

import pytest
from pytest import approx

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.only_for_pool_type(1)  # only for metapools
class TestMetaExchangeUnderlying:
    @pytest.mark.parametrize("sending,receiving", filter(lambda k: 0 in k, itertools.permutations(range(4), 2)))
    def test_amounts(self, bob, swap, underlying_tokens, sending, receiving, meta_decimals, base_pool_decimals):
        underlying_decimals = [meta_decimals] + base_pool_decimals
        underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
        amount = 10 ** underlying_decimals[sending]

        if sending > 0:
            underlying_tokens[sending]._mint_for_testing(bob, amount)

        initial_amount = underlying_tokens[sending].balanceOf(bob)
        initial_amount_receiving = underlying_tokens[receiving].balanceOf(bob)

        swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)
        assert underlying_tokens[sending].balanceOf(bob) == initial_amount - amount

        received = underlying_tokens[receiving].balanceOf(bob) - initial_amount_receiving
        assert 0.999 <= received / amount < 1

    @pytest.mark.parametrize("sending,receiving", filter(lambda k: 0 in k, itertools.permutations(range(4), 2)))
    def test_fees(
        self,
        bob,
        swap,
        underlying_tokens,
        sending,
        receiving,
        meta_decimals,
        base_pool,
        base_pool_decimals,
    ):
        underlying_decimals = [meta_decimals] + base_pool_decimals
        underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
        amount = 10000 * 10 ** underlying_decimals[sending]
        underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)
        swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

        admin_idx = min(1, receiving)
        admin_fee = swap.admin_balances(admin_idx)

        expected = 2 * 10 ** underlying_decimals[admin_idx]
        if admin_idx == 1:
            expected = expected * 10**18 // base_pool.get_virtual_price()
        assert expected / admin_fee == approx(1, rel=1e-3)

    @pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
    def test_min_dy_underlying(
        self, bob, swap, underlying_tokens, sending, receiving, meta_decimals, base_pool_decimals
    ):
        underlying_decimals = [meta_decimals] + base_pool_decimals
        underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
        amount = 10 ** underlying_decimals[sending]
        underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)

        expected = swap.get_dy_underlying(sending, receiving, amount)
        received = swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

        assert abs(expected - received) / received < 0.00001
