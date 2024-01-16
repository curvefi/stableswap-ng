import itertools

import boa
import pytest

MAX_COINS = 8


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_find_pool_for_coins(factory, meta_swap, underlying_tokens, sending, receiving):
    assert (
        factory.find_pool_for_coins(underlying_tokens[sending].address, underlying_tokens[receiving].address)
        == meta_swap.address
    )


@pytest.mark.parametrize("idx", range(1, 4))
def test_find_pool_for_coins_underlying(factory, meta_swap, underlying_tokens, idx):
    assert factory.find_pool_for_coins(underlying_tokens[0], underlying_tokens[idx]) == meta_swap.address
    assert factory.find_pool_for_coins(underlying_tokens[idx], underlying_tokens[0]) == meta_swap.address


def test_get_meta_n_coins(factory, meta_swap):
    assert factory.get_meta_n_coins(meta_swap.address) == (2, 4)


def test_get_underlying_coins(factory, meta_swap, underlying_tokens):
    tokens = [underlying_tokens[0]] + underlying_tokens[2:]
    assert factory.get_underlying_coins(meta_swap.address) == [t.address for t in tokens]


def test_get_underlying_decimals(factory, meta_swap, base_pool_decimals):
    assert factory.get_underlying_decimals(meta_swap.address) == [18] + base_pool_decimals


def test_get_metapool_rates(meta_setup, factory, meta_swap, base_pool, base_pool_lp_token):
    assert factory.get_metapool_rates(meta_swap.address) == [10**18, base_pool.get_virtual_price()]


def test_get_underlying_balances(meta_setup, factory, meta_swap, base_pool):
    assert factory.get_metapool_rates(meta_swap.address) == [10**18, base_pool.get_virtual_price()]


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(1, 4), 2))
def test_find_pool_underlying_base_pool_only(factory, underlying_tokens, sending, receiving, zero_address):
    assert factory.find_pool_for_coins(underlying_tokens[sending], underlying_tokens[receiving]) == zero_address


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(2, 5), 2))
def test_get_coin_indices_underlying(factory, meta_swap, sending, receiving, underlying_tokens):
    i, j, is_underlying = factory.get_coin_indices(meta_swap, underlying_tokens[sending], underlying_tokens[receiving])
    assert i == sending - 1
    assert j == receiving - 1
    assert is_underlying is True


@pytest.mark.parametrize("idx", range(1, 4))
def test_get_coin_indices_reverts(factory, meta_swap, base_pool_lp_token, underlying_tokens, idx):
    with boa.reverts():
        factory.get_coin_indices(meta_swap.address, base_pool_lp_token.address, underlying_tokens[idx])


def test_get_implementation_address(factory, meta_swap, amm_implementation_meta):
    assert factory.get_implementation_address(meta_swap.address) == amm_implementation_meta.address


def test_is_meta(factory, meta_swap):
    assert factory.is_meta(meta_swap.address) is True
