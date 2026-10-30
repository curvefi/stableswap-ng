import random
from math import exp, log

import boa
import pytest
from boa.test import strategy
from hypothesis import HealthCheck, given, settings

from tests.constants import POOL_TYPES, TOKEN_TYPES
from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils import approx
from tests.utils.tokens import mint_for_testing

SETTINGS = {"max_examples": 10, "deadline": None, "suppress_health_check": [HealthCheck.function_scoped_fixture]}
pytestmark = pytest.mark.usefixtures("initial_setup")

MA_EXP_TIME = 866
# Mirrors SPOT_BAND_NUM / SPOT_BAND_DEN in the contracts: the stored spot price is
# clamped to [ema / K, ema * K], where ema is the EMA computed in the same update.
SPOT_BAND = 11 / 10


def clamp_spot(p, ema):
    return min(max(p, ema / SPOT_BAND), ema * SPOT_BAND)


def precision(swap):
    try:
        return 1e-2 if swap._immutables.pool_contains_rebasing_tokens else 1e-5
    except AttributeError:  # ABIContract (vvm-compiled) has no _immutables
        return 1e-2


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
    prec = precision(swap)
    for n in range(coins):
        # No time has passed since the last oracle update, so the EMA is still
        # 10**18 and the stored spot is clamped to [10**18 / K, 10**18 * K]:
        _p = clamp_spot(swap.get_p(n), 10**18)
        assert approx(swap.last_price(n), _p, prec)
        assert approx(swap.price_oracle(n), 10**18, prec)

        p_amm.append(_p)

    # time travel dt amount:
    boa.env.time_travel(dt)

    # calculate weights based on time travelled:
    w = exp(-dt / MA_EXP_TIME)

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

    # the stored spot can't leave [ema / K, ema * K] (ema is still 10**18 here):
    ema0 = basic_swap.price_oracle(0)
    assert approx(ema0, 10**18, 1e-5)
    assert ema0 / SPOT_BAND * (1 - 1e-9) <= basic_swap.last_price(0) <= ema0 * SPOT_BAND * (1 + 1e-9)

    # time travel
    dt = 500 * 12
    boa.env.time_travel(blocks=500)

    # check if price oracle is way too high: the EMA can't move by more than
    # (K - 1) * (1 - exp(-dt / ma_exp_time)) from a single swap
    p_oracle_after = basic_swap.price_oracle(0)
    w = exp(-dt / MA_EXP_TIME)

    assert p_oracle_after <= ema0 * (1 + (SPOT_BAND - 1) * (1 - w)) * (1 + 1e-5)
    assert p_oracle_after < 2 * 10**18


@pytest.mark.only_basic_pool
def test_initial_deposit_sets_oracle(basic_swap, pool_type):
    # the first deposit (re)instantiates the price oracle at the actual spot, so a pool
    # whose fair price is far from 1 does not have to walk there through the band
    assert pool_type == POOL_TYPES["basic"]
    prec = precision(basic_swap)
    p_spot = basic_swap.get_p(0)
    assert approx(basic_swap.last_price(0), p_spot, prec)
    assert approx(basic_swap.price_oracle(0), p_spot, prec)


@pytest.mark.only_basic_pool
@pytest.mark.parametrize("i,j", [(0, 1), (1, 0)])
def test_spot_band(basic_swap, bob, pool_tokens, pool_token_types, pool_type, decimals, i, j):
    assert pool_type == POOL_TYPES["basic"]
    prec = 1e-2 if TOKEN_TYPES["rebasing"] in pool_token_types else 1e-5

    # swap the whole pool balance one way: spot leaves the band on side i
    amount_in = INITIAL_AMOUNT * 10 ** decimals[i]
    mint_for_testing(bob, amount_in, pool_tokens[i], False)
    basic_swap.exchange(i, j, amount_in, 0, sender=bob)

    # EMA computed in the same update is still 10**18, stored spot sits on the band edge:
    ema0 = basic_swap.price_oracle(0)
    p_spot = basic_swap.get_p(0)
    last_p = basic_swap.last_price(0)
    assert approx(ema0, 10**18, prec)
    if i == 0:
        assert p_spot > ema0 * SPOT_BAND
        assert approx(last_p, ema0 * SPOT_BAND, 1e-9)
    else:
        assert p_spot < ema0 / SPOT_BAND
        assert approx(last_p, ema0 / SPOT_BAND, 1e-9)

    # after dt the EMA moved towards the clamped spot, i.e. by at most (K - 1) * (1 - w):
    dt = MA_EXP_TIME
    boa.env.time_travel(dt)
    w = exp(-dt / MA_EXP_TIME)
    p_oracle = basic_swap.price_oracle(0)
    assert approx(p_oracle, ema0 * w + last_p * (1 - w), 1e-5)
    assert abs(p_oracle / ema0 - 1) <= (SPOT_BAND - 1) * (1 - w) * (1 + 1e-5)


@given(
    amount=strategy("uint256", min_value=1, max_value=10**5),
    dt0=strategy("uint256", min_value=0, max_value=10**6),
    dt=strategy("uint256", min_value=0, max_value=10**6),
)
@settings(**SETTINGS)
def test_D_ema(swap, bob, pool_tokens, underlying_tokens, decimals, amount, dt0, dt, math_implementation):
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
    w = exp(-dt / MA_EXP_TIME)

    # check:
    D1 = get_D(swap, math_implementation)
    D1 = int(D0 * w + D1 * (1 - w))
    assert approx(swap.D_oracle(), D1, 1e-5)
