import boa
import pytest


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_find_pool_for_coins(factory, swap, plain_tokens, sending, receiving):
    assert factory.find_pool_for_coins(plain_tokens[sending].address, plain_tokens[receiving].address) == swap.address


def test_get_n_coins(factory, swap, plain_tokens, pool_size):
    assert factory.get_n_coins(swap.address) == 2


def test_get_coins(factory, swap, plain_tokens, pool_size):
    assert factory.get_coins(swap.address) == [pt.address for pt in plain_tokens]


def test_get_decimals(factory, swap, decimals):
    assert factory.get_decimals(swap.address) == decimals


def test_get_balances(factory, swap, pool_size):
    assert factory.get_balances(swap.address) == [swap.balances(i) for i in range(pool_size)]


def test_get_underlying_balances(factory, basic_swap):
    with boa.reverts() as e:
        factory.get_underlying_balances(basic_swap.address)
        assert str(e) == "dev: pool is not a metapool"


def test_get_A(factory, swap):
    assert factory.get_A(swap.address) == swap.A()


def test_get_fees(factory, swap):
    assert factory.get_fees(swap.address) == (swap.fee(), swap.admin_fee())


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_get_coin_indices(factory, swap, sending, receiving, plain_tokens):
    i, j, is_underlying = factory.get_coin_indices(
        swap.address, plain_tokens[sending].address, plain_tokens[receiving].address
    )
    assert i == sending
    assert j == receiving


def test_get_implementation_address(factory, swap, amm_implementation):
    assert factory.get_implementation_address(swap.address) == amm_implementation.address


def test_is_meta(factory, swap):
    assert factory.is_meta(swap.address) is False


def test_get_pool_types(factory, swap, pool_token_types):
    assert factory.get_pool_asset_types(swap.address) == list(pool_token_types)
