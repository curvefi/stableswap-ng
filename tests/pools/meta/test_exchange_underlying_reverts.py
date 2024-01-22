import itertools

import boa
import pytest

pytestmark = pytest.mark.usefixtures("meta_setup")


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
def test_min_dy_too_high(bob, meta_swap, underlying_tokens, meta_decimals, base_pool_decimals, sending, receiving):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount = 10 ** underlying_decimals[sending]
    underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)

    min_dy = meta_swap.get_dy_underlying(sending, receiving, int(amount * 1.0001))
    with boa.reverts():
        meta_swap.exchange_underlying(sending, receiving, amount, min_dy, sender=bob)


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
def test_insufficient_balance(
    bob, meta_swap, underlying_tokens, meta_decimals, base_pool_decimals, sending, receiving, zero_address
):
    underlying_decimals = [meta_decimals] + base_pool_decimals
    underlying_tokens = [underlying_tokens[0], *underlying_tokens[2:]]
    amount = 10 ** underlying_decimals[sending]
    underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)
    underlying_tokens[sending].transfer(zero_address, underlying_tokens[sending].balanceOf(bob), sender=bob)

    underlying_tokens[sending]._mint_for_testing(bob, amount, sender=bob)
    with boa.reverts():
        meta_swap.exchange_underlying(sending, receiving, amount + 1, 0, sender=bob)


@pytest.mark.parametrize("idx", range(4))
def test_same_coin(bob, meta_swap, idx):
    with boa.reverts():
        meta_swap.exchange_underlying(idx, idx, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [-1, -(2**127)])
def test_i_below_zero(bob, meta_swap, idx):
    with boa.reverts():
        meta_swap.exchange_underlying(idx, 0, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [4, 2**127 - 1])
def test_i_above_n_coins(bob, meta_swap, idx):
    with boa.reverts():
        meta_swap.exchange_underlying(idx, 0, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [-1, -(2**127)])
def test_j_below_zero(bob, meta_swap, idx):
    with boa.reverts():
        meta_swap.exchange_underlying(0, idx, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [4, 2**127 - 1])
def test_j_above_n_coins(bob, meta_swap, idx):
    with boa.reverts():
        meta_swap.exchange_underlying(0, idx, 0, 0, sender=bob)
