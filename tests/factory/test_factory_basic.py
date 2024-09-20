import boa
import pytest


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_find_pool_for_coins(factory, basic_swap, pool_tokens, sending, receiving):
    assert (
        factory.find_pool_for_coins(pool_tokens[sending].address, pool_tokens[receiving].address)
        == basic_swap.address
    )


def test_get_n_coins(factory, basic_swap, pool_tokens, pool_size):
    assert factory.get_n_coins(basic_swap.address) == 2


def test_get_coins(factory, basic_swap, pool_tokens, pool_size):
    assert factory.get_coins(basic_swap.address) == [pt.address for pt in pool_tokens]


def test_get_decimals(factory, basic_swap, decimals):
    assert factory.get_decimals(basic_swap.address) == decimals


def test_get_balances(factory, basic_swap, pool_size):
    assert factory.get_balances(basic_swap.address) == [
        basic_swap.balances(i) for i in range(pool_size)
    ]


def test_get_underlying_balances(factory, basic_swap):
    with boa.reverts() as e:
        factory.get_underlying_balances(basic_swap.address)
        assert str(e) == "dev: pool is not a metapool"


def test_get_A(factory, basic_swap):
    assert factory.get_A(basic_swap.address) == basic_swap.A()


def test_get_fees(factory, basic_swap):
    assert factory.get_fees(basic_swap.address) == (basic_swap.fee(), basic_swap.admin_fee())


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_get_coin_indices(factory, basic_swap, sending, receiving, pool_tokens):
    i, j, is_underlying = factory.get_coin_indices(
        basic_swap.address, pool_tokens[sending].address, pool_tokens[receiving].address
    )
    assert i == sending
    assert j == receiving


def test_get_implementation_address(factory, basic_swap, amm_implementation):
    assert factory.get_implementation_address(basic_swap.address) == amm_implementation.address


def test_is_meta(factory, basic_swap):
    assert factory.is_meta(basic_swap.address) is False


def test_get_pool_types(factory, basic_swap, pool_token_types):
    assert factory.get_pool_asset_types(basic_swap.address) == list(pool_token_types)
