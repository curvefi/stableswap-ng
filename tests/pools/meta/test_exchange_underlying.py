import itertools

import pytest

from tests.utils import approx

pytestmark = pytest.mark.usefixtures("meta_setup")

permutations = list(itertools.permutations(range(4), 2))  # 0,1...3,2


@pytest.mark.only_plain_tokens
@pytest.mark.parametrize("sending,receiving", [p for p in permutations if 0 in p])
def test_amounts(bob, meta_swap, underlying_tokens, sending, receiving, meta_decimals, base_pool_decimals):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount_sent = 10 ** underlying_decimals[sending]

    if sending > 0 and underlying_tokens[sending].balanceOf(bob) < amount_sent:
        underlying_tokens[sending]._mint_for_testing(bob, amount_sent)

    expected_received = meta_swap.get_dy_underlying(sending, receiving, amount_sent)
    received_true = meta_swap.exchange_underlying(sending, receiving, amount_sent, 0, sender=bob)  # noqa: F841
    assert approx(received_true, expected_received, 1e-3)


@pytest.mark.only_plain_tokens
@pytest.mark.parametrize("sending,receiving", permutations)
def test_min_dy_underlying(bob, meta_swap, underlying_tokens, sending, receiving, meta_decimals, base_pool_decimals):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount = 10 ** underlying_decimals[sending]
    underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)

    expected = meta_swap.get_dy_underlying(sending, receiving, amount)
    received = meta_swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

    assert approx(expected, received, 1e-3)
