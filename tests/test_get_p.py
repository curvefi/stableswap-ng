import random
from math import log

import pytest
from boa.test import strategy
from hypothesis import given, settings

from tests.utils.tokens import mint_for_testing

SETTINGS = {"max_examples": 100, "deadline": None}
pytestmark = pytest.mark.usefixtures("initial_setup")


@given(
    amount=strategy("uint256", min_value=1, max_value=10**6),
)
@settings(**SETTINGS)
def test_get_p_similar(swap, views_implementation, bob, pool_tokens, decimals, amount):

    for token in pool_tokens:
        if "IS_UP" in token._immutables.__dict__.keys() and not token._immutables.IS_UP:
            return  # TODO: rebasing tokens that rebase downwards are causing trouble here.

    i, j = random.sample(range(swap.N_COINS()), 2)

    # calc amount in:
    amount_in = amount * 10 ** (decimals[i])

    if amount_in > pool_tokens[i].balanceOf(bob):
        mint_for_testing(bob, amount_in, pool_tokens[i], False)

    # swap first
    pool_tokens[i].approve(swap, 2**256 - 1, sender=bob)
    swap.exchange(i, j, amount_in, 0, sender=bob)

    # numeric prices:
    p_numeric = []
    for n in range(1, swap.N_COINS()):

        expected_jth_out = views_implementation.get_dy(0, n, 10**18, swap)
        p_numeric.append(swap.stored_rates(0) / expected_jth_out)

    # amm prices:
    p_amm = []
    for n in range(swap.N_COINS() - 1):
        p_amm.append(swap.get_p(n) * swap.stored_rates(n + 1) / 10**36)

    # compare
    for n in range(swap.N_COINS() - 1):
        assert abs(log(p_amm[n] / p_numeric[n])) < 1e-3, f"p_amm: {p_amm}, p_numeric: {p_numeric}"
