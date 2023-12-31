import itertools

import pytest

from tests.utils import approx

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.skip_oracle_tokens
@pytest.mark.skip_rebasing_tokens
@pytest.mark.parametrize("sending,receiving", filter(lambda k: 0 in k, itertools.permutations(range(4), 2)))
def test_amounts(bob, swap, underlying_tokens, sending, receiving, meta_decimals, base_pool_decimals):

    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount_sent = 10 ** underlying_decimals[sending]

    if sending > 0 and underlying_tokens[sending].balanceOf(bob) < amount_sent:
        underlying_tokens[sending]._mint_for_testing(bob, amount_sent)

    expected_received = swap.get_dy_underlying(sending, receiving, amount_sent)
    received_true = swap.exchange_underlying(sending, receiving, amount_sent, 0, sender=bob)  # noqa: F841
    assert approx(received_true, expected_received, 1e-3)


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.skip_rebasing_tokens
@pytest.mark.skip_oracle_tokens
@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
def test_min_dy_underlying(bob, swap, underlying_tokens, sending, receiving, meta_decimals, base_pool_decimals):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount = 10 ** underlying_decimals[sending]
    underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)

    expected = swap.get_dy_underlying(sending, receiving, amount)
    received = swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

    assert approx(expected, received, 1e-3)
