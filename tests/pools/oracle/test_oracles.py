import random
from math import exp, log

import boa
import pytest
from boa.test import strategy
from hypothesis import HealthCheck, given, settings

from tests.utils import approx
from tests.utils.tokens import mint_for_testing

SETTINGS = {
    "max_examples": 10,
    "deadline": None,
    "suppress_health_check": [HealthCheck.function_scoped_fixture],
}
pytestmark = pytest.mark.usefixtures("initial_setup")


def get_D(swap, math):
    _rates = swap.stored_rates()
    _balances = swap.internal._balances()
    xp = swap.internal._xp_mem(_rates, _balances)
    amp = swap.internal._A()
    return math.get_D(xp, amp, swap.N_COINS())


def check_oracle(swap, dt):
    # amm prices:
    p_amm = []
    coins = swap.N_COINS() - 1
    assert 0 < coins < 10
    if swap._immutables.pool_contains_rebasing_tokens:
        prec = 1e-2
    else:
        prec = 1e-5
    for n in range(coins):
        _p = swap.get_p(n)
        if _p > 2 * 10**18 or _p < 0.5 * 10**18:
            # oracle price can't go more than 2 (but can be less than 0.5)
            # Contract code: min(spot_price[i], 2 * 10**18),  # <----- Cap spot value by 2.
            # If first (idx = 0) token depegs, then spot_price[1] can become >> 2, but will be capped
            # If second (idx = 1) token depegs, then spot_price[1] can become << 0.5, but _WILL_NOT_ be capped
            pytest.skip("Oracle threshold exceeded, xfail")
        assert approx(swap.last_price(n), _p, prec)
        assert approx(swap.price_oracle(n), 10**18, prec)

        p_amm.append(_p)

    # time travel dt amount:
    boa.env.time_travel(dt)

    # calculate weights based on time travelled:
    w = exp(-dt / 866)

    # check:
    for n in range(coins):
        p1 = int(10**18 * w + p_amm[n] * (1 - w))
        assert approx(swap.price_oracle(n), p1, prec)


@given(amount=strategy("uint256", min_value=1, max_value=10**6))
@settings(**SETTINGS)
def test_get_p(swap, views_implementation, bob, pool_tokens, decimals, amount):
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
    stored_rates = swap.stored_rates()
    for n in range(1, swap.N_COINS()):
        expected_jth_out = views_implementation.get_dy(0, n, 10**18, swap)
        p_numeric.append(stored_rates[0] / expected_jth_out)

    # amm prices:
    p_amm = []
    for n in range(swap.N_COINS() - 1):
        p_amm.append(swap.get_p(n) * stored_rates[n + 1] / 10**36)

    # compare
    for n in range(swap.N_COINS() - 1):
        assert abs(log(p_amm[n] / p_numeric[n])) < 1e-3, f"p_amm: {p_amm}, p_numeric: {p_numeric}"


@given(
    amount=strategy("uint256", min_value=1, max_value=10**5),
    dt0=strategy("uint256", min_value=0, max_value=10**6),
    dt=strategy("uint256", min_value=0, max_value=10**6),
)
@settings(**SETTINGS)
def test_price_ema_exchange(swap, bob, pool_tokens, underlying_tokens, decimals, amount, dt0, dt):
    i, j = random.sample(range(swap.N_COINS()), 2)

    # calc amount in:
    amount_in = amount * 10 ** (decimals[i])

    # mint tokens for bob if he needs:
    if amount_in > pool_tokens[i].balanceOf(bob):
        mint_for_testing(bob, amount_in, pool_tokens[i], False)

    boa.env.time_travel(dt0)
    swap.exchange(i, j, amount_in, 0, sender=bob)

    check_oracle(swap, dt)


@given(
    amount=strategy("uint256", min_value=1, max_value=10**5),
    dt0=strategy("uint256", min_value=0, max_value=10**6),
    dt=strategy("uint256", min_value=0, max_value=10**6),
)
@settings(**SETTINGS)
# @pytest.mark.parametrize("amount, dt0, dt", [(83800, 12, 12)])
def test_price_ema_remove_one(swap, alice, amount, dt0, dt):
    i = random.choice(range(swap.N_COINS()))
    alice_lp_bal = swap.balanceOf(alice)
    amt_to_remove = int(alice_lp_bal * amount / (10**5 - 1))
    boa.env.time_travel(dt0)
    swap.remove_liquidity_one_coin(amt_to_remove, i, 0, sender=alice)
    check_oracle(swap, dt)


@given(
    amount=strategy("uint256", min_value=1, max_value=10**5),
    dt0=strategy("uint256", min_value=0, max_value=10**6),
    dt=strategy("uint256", min_value=0, max_value=10**6),
)
@settings(**SETTINGS)
# @pytest.mark.parametrize("amount, dt0, dt", [(99190, 12, 12)])
# @pytest.mark.parametrize("amount, dt0, dt", [(94741, 12, 12)])
def test_price_ema_remove_imbalance(swap, alice, dt0, dt, pool_size, deposit_amounts, amount):
    i = random.choice(range(swap.N_COINS()))
    # i = 1
    amounts = [0] * pool_size
    fraction = min(
        0.8, amount / (10**5)
    )  # if lots of liquidity is removed (>80% onesided) - oracle gets off by up to 10%
    # because new_balances in upkeep_oracles and _balances() in get_p are different (fees?)
    # and D's are different => get_p differs from last_price
    amounts[i] = int(deposit_amounts[i] * fraction)
    lp_balance = pool_size * deposit_amounts[i]
    print("/n get_p", swap.get_p(0) / 1e18)
    print("last_price", swap.last_price(0) / 1e18)

    boa.env.time_travel(dt0)
    swap.remove_liquidity_imbalance(amounts, lp_balance, sender=alice)
    print("get_p", swap.get_p(0) / 1e18)
    print("last_price", swap.last_price(0) / 1e18)
    check_oracle(swap, dt)


@given(amount=strategy("uint256", min_value=10**9, max_value=10**15))
@settings(**SETTINGS)
def test_manipulate_ema(basic_swap, bob, pool_tokens, underlying_tokens, decimals, amount):
    # calc amount in:
    amount_in = amount * 10 ** (decimals[0])

    # mint tokens for bob if he needs:
    if amount_in > pool_tokens[0].balanceOf(bob):
        mint_for_testing(bob, amount_in, pool_tokens[0], False)

    # do large swap
    try:
        basic_swap.exchange(0, 1, amount_in, 0, sender=bob)
    except boa.BoaError:
        return  # we're okay with failure to manipulate here

    # time travel
    boa.env.time_travel(blocks=500)

    # check if price oracle is way too high
    p_oracle_after = basic_swap.price_oracle(0)

    assert p_oracle_after < 2 * 10**18


@given(
    amount=strategy("uint256", min_value=1, max_value=10**5),
    dt0=strategy("uint256", min_value=0, max_value=10**6),
    dt=strategy("uint256", min_value=0, max_value=10**6),
)
@settings(**SETTINGS)
def test_D_ema(
    swap, bob, pool_tokens, underlying_tokens, decimals, amount, dt0, dt, math_implementation
):
    i, j = random.sample(range(swap.N_COINS()), 2)

    # calc amount in:
    amount_in = amount * 10 ** (decimals[i])

    # mint tokens for bob if he needs:
    if amount_in > pool_tokens[i].balanceOf(bob):
        mint_for_testing(bob, amount_in, pool_tokens[i], False)

    boa.env.time_travel(dt0)
    swap.exchange(i, j, amount_in, 0, sender=bob)

    # check D oracle before time travel (shouldnt really change):
    D0 = get_D(swap, math_implementation)
    assert approx(swap.D_oracle(), D0, 1e-5)

    # time travel dt amount:
    boa.env.time_travel(dt)

    # calculate weights based on time travelled:
    w = exp(-dt / 866)

    # check:
    D1 = get_D(swap, math_implementation)
    D1 = int(D0 * w + D1 * (1 - w))
    assert approx(swap.D_oracle(), D1, 1e-5)
