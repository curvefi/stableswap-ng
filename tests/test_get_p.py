import random
from math import exp, log

import boa
import pytest
from boa.test import strategy
from hypothesis import given, settings

from tests.utils.tokens import mint_for_testing

SETTINGS = {"max_examples": 1000, "deadline": None}
pytestmark = pytest.mark.usefixtures("initial_setup")


def approx(x1: int, x2: int, precision: int, abs_precision=None):
    if precision >= 1:
        return True
    result = False
    if abs_precision is not None:
        result = abs(x2 - x1) <= abs_precision
    else:
        abs_precision = 0
    if x2 == 0:
        return abs(x1) <= abs_precision
    elif x1 == 0:
        return abs(x2) <= abs_precision
    return result or (abs(log(x1 / x2)) <= precision)


@given(
    amount=strategy("uint256", min_value=1, max_value=10**6),
)
@settings(**SETTINGS)
def test_get_p(swap, views_implementation, bob, pool_tokens, decimals, amount):

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


@given(
    amount=strategy("uint256", min_value=1, max_value=10**5),
    dt0=strategy("uint256", min_value=0, max_value=10**6),
    dt=strategy("uint256", min_value=0, max_value=10**6),
)
@settings(**SETTINGS)
def test_ema(swap, bob, pool_tokens, underlying_tokens, decimals, amount, dt0, dt):

    for token in pool_tokens:
        if "IS_UP" in token._immutables.__dict__.keys() and not token._immutables.IS_UP:
            return  # TODO: rebasing tokens that rebase downwards are causing trouble here.

    i, j = random.sample(range(swap.N_COINS()), 2)

    # calc amount in:
    amount_in = amount * 10 ** (decimals[i])

    # mint tokens for bob if he needs:
    if amount_in > pool_tokens[i].balanceOf(bob):
        mint_for_testing(bob, amount_in, pool_tokens[i], False)

    boa.env.time_travel(dt0)
    swap.exchange(i, j, amount, 0, sender=bob)

    # amm prices:
    p_amm = []
    for n in range(swap.N_COINS() - 1):

        _p = swap.get_p(n)

        assert approx(swap.last_price(n), _p, 1e-5)
        assert approx(swap.price_oracle(n), 10**18, 1e-5)

        p_amm.append(_p)

    # time travel dt amount:
    boa.env.time_travel(dt)

    # calculate weights based on time travelled:
    w = exp(-dt / 866)

    # check:
    for n in range(swap.N_COINS() - 1):

        p1 = int(10**18 * w + p_amm[n] * (1 - w))
        assert approx(swap.price_oracle(n), p1, 1e-5)
