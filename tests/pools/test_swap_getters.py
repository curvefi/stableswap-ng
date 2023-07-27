import pytest
from boa.test import strategy
from hypothesis import given, settings

SETTINGS = {"max_examples": 100, "deadline": None}


@given(
    amount_in=strategy("decimal", min_value=0.001, max_value=10**6),
    i=strategy("uint", min_value=0, max_value=2),
    j=strategy("uint", min_value=0, max_value=2),
)
@settings(**SETTINGS)
def test_get_dx(i, j, amount_in, swap, factory, initial_setup):

    n_coins = swap.N_COINS()
    if i == j or max(i, j) >= n_coins:
        return

    _token_i_precision = 10 ** factory.get_decimals(swap)[i]
    _amount_in = int(amount_in * _token_i_precision)

    expected_out = swap.get_dy(i, j, _amount_in)
    approx_in = swap.get_dx(i, j, expected_out)

    # not accurate, but close enough:
    assert _amount_in == pytest.approx(approx_in, 1e-2)
