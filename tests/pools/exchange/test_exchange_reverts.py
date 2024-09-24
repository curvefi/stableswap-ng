import boa
import pytest
import time

pytestmark = pytest.mark.usefixtures("initial_setup")


# @pytest.mark.all_token_pairs
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_insufficient_balance(
    charlie,
    pool_tokens,
    underlying_tokens,
    swap,
    sending,
    receiving,
    decimals,
    pool_type,
    pool_token_types,
    metapool_token_type,
):
    amount = 10 ** decimals[sending]
    if (pool_type == 0 and pool_token_types[sending] == 2) or (
        pool_type == 1 and metapool_token_type == 2 and sending == 0
    ):
        pytest.skip("Rebasing token problem")
    # Interesting case: transferring 0 shares of a rebasing token. In the
    # rebasing mock, _shares = min(self.shares[_from], _shares) sets
    # shares_to_send to 0 and triggers a rebase. This results in the pool
    # receiving 0 tokens, but the rebase makes it think it has more tokens
    # than before. This does not cause a revert, and the user gets some
    # rebase tokens for free.
    #
    # The current mock triggers a rebase on transfer, so a rebase can occur
    # during the exchange. However, in production, rebases are triggered by
    # oracles. Therefore, exchange_received must be used to put rebase
    # inside a trade, and this fcn does not work with rebasing tokens.
    #
    # Even if a user can trigger a token-wide rebase, it must occur during
    # the transfer of tokens. Otherwise, the pool is safe.
    # !!!!!!! Fixed with changing rebase logic to not rebase at 0 transfer !!!!!!!!!!
    #
    # what is not fixed - is that this min function transfers 0 evein if
    # non-0 is requested, and this bypasses dx > 0 assert in the contract,
    # resulting in a 0->swap (that fails the test in some cases)
    # Thus still skipping problematic tests.

    for token in pool_tokens + underlying_tokens:
        assert token.balanceOf(charlie) == 0
    with boa.reverts():
        swap.exchange(sending, receiving, amount, 0, sender=charlie)
    # time.sleep(10)


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
    amount = 10_000 * 10 ** decimals[sending]
    min_dy = swap.get_dy(sending, receiving, amount)

    if swap._immutables.pool_contains_rebasing_tokens:
        min_dy_test = int(min_dy * 1.001)
    else:
        min_dy_test = min_dy + 1
    with boa.reverts():
        swap.exchange(sending, receiving, amount, min_dy_test, sender=bob)


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
