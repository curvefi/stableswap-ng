import boa
import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


# @pytest.mark.extensive_token_pairs
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_insufficient_balance(
    charlie, pool_tokens, underlying_tokens, swap, sending, receiving, decimals
):
    amount = 10 ** decimals[sending]

    for token in pool_tokens + underlying_tokens:
        assert token.balanceOf(charlie) == 0

    # Charlie doesn't have any tokens, all balances are 0
    with boa.reverts(), boa.env.prank(charlie):
        swap.exchange(sending, receiving, amount + 1, 0, sender=charlie)


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_zero_amount_swap(
    charlie,
    pool_tokens,
    underlying_tokens,
    swap,
    sending,
    receiving,
    decimals,
    contains_rebasing_tokens,
):
    with boa.reverts():
        swap.exchange(sending, receiving, 0, 0, sender=charlie)


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_min_dy_too_high(bob, swap, sending, receiving, decimals):
    amount = 10 ** decimals[sending]
    min_dy = swap.get_dy(sending, receiving, amount)
    with boa.reverts():
        swap.exchange(sending, receiving, amount, min_dy + 2, sender=bob)


@pytest.mark.parametrize("idx", range(2))
def test_same_coin(bob, swap, idx):
    with boa.reverts():
        swap.exchange(idx, idx, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [-1, -(2**127)])
def test_i_below_zero(bob, swap, idx):
    with boa.reverts():
        swap.exchange(idx, 0, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [9, 2**127 - 1])
def test_i_above_n_coins(bob, swap, idx):
    with boa.reverts():
        swap.exchange(idx, 0, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [-1, -(2**127)])
def test_j_below_zero(bob, swap, idx):
    with boa.reverts():
        swap.exchange(0, idx, 0, 0, sender=bob)


@pytest.mark.parametrize("idx", [9, 2**127 - 1])
def test_j_above_n_coins(bob, swap, idx):
    with boa.reverts():
        swap.exchange(0, idx, 0, 0, sender=bob)


def test_nonpayable(swap, bob):
    with boa.reverts():
        swap.exchange(0, 1, 0, 0, sender=bob, value=1)
