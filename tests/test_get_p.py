from math import log

import pytest
from boa.test import strategy
from hypothesis import given, settings

from tests.utils.tokens import mint_for_testing

SETTINGS = {"max_examples": 100, "deadline": None}
pytestmark = pytest.mark.usefixtures("initial_setup")


def _get_prices_numeric(swap, decimals, i):

    numeric_quote = []

    if i == 0:  # selling 0th token

        sell_token_precision = 10 ** decimals[0]

        for j in range(1, swap.N_COINS):

            amount_in = sell_token_precision // 100
            expected_out = swap.get_dy(0, j, amount_in)

            numeric_quote.append(int(expected_out * sell_token_precision / amount_in))

    else:

        for j in range(1, swap.N_COINS()):

            sell_token_precision = 10 ** decimals[i]
            amount_in = sell_token_precision // 100
            expected_out = swap.get_dy(i, 0, amount_in)

            numeric_quote.append(int(expected_out * sell_token_precision / amount_in))

    return numeric_quote


def _get_prices_amm(swap):

    amm_quote = []
    for i in range(swap.N_COINS() - 1):
        amm_quote.append(swap.get_p(i))

    return amm_quote


@given(
    amount=strategy("uint256", max_value=10**6),
)
@settings(**SETTINGS)
@pytest.mark.parametrize("i", list(range(8)))
@pytest.mark.parametrize("j", list(range(8)))
def test_get_p_similar(swap, charlie, pool_type, pool_tokens, underlying_tokens, decimals, i, j, amount):

    if i == j or max(i, j) == swap.N_COINS() or amount == 0:
        return

    # calc amount in:
    amount_in = amount * 10 ** (decimals[i])

    if amount_in > pool_tokens[i].balanceOf(charlie):
        mint_for_testing(charlie, amount_in, pool_tokens[i], False)

    # swap first
    pool_tokens[i].approve(swap, 2**256 - 1, sender=charlie)
    swap.exchange(i, j, amount_in, 0, sender=charlie)

    p_amm = _get_prices_amm(swap)
    p_numeric = _get_prices_numeric(swap, decimals, i)

    for n in range(swap.N_COINS()):
        assert abs(log(p_amm[n] / p_numeric[n])) < 1e-5


@given(
    dollar_amount=strategy("uint256", min_value=5 * 10**4, max_value=5 * 10**8),
)
@settings(**SETTINGS)
@pytest.mark.parametrize("i", list(range(8)))
@pytest.mark.parametrize("j", list(range(8)))
def test_get_p_dupm(swap, charlie, pool_type, pool_tokens, underlying_tokens, decimals, i, j, amount):

    if i == j or max(i, j) == swap.N_COINS():
        return

    pass


@given(
    dollar_amount=strategy("uint256", min_value=5 * 10**4, max_value=5 * 10**8),
)
@settings(**SETTINGS)
@pytest.mark.parametrize("i", list(range(8)))
@pytest.mark.parametrize("j", list(range(8)))
def test_get_p_pupm(swap, charlie, pool_type, pool_tokens, underlying_tokens, decimals, i, j, amount):

    if i == j or max(i, j) == swap.N_COINS():
        return

    pass
