import boa
import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


# @pytest.mark.extensive_token_pairs
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
        # interesting case, we transfer 0 shares of rebasing token because
        # _shares = min(self.shares[_from], _shares) in rebasing mock sets shares_to_send to 0
        # and triggers rebase, so pool gets 0 transfer in, but rebase
        # makes it think it has more tokens than before => no revert and user gets
        # some rebase tokens for free. See if anything like that is ever possible in prod,
        # or it's just bad mock
        # some more investigations - current mock triggers rebase on transfer
        # so rebase can be triggered in the middle of the exchange
        # however in prod rebase is triggered by oracles, so exchange_received must be used
        # and it does not work with rebasing tokens
        # so - even if user can trigger token-wide rebase - he must do so during transfer of tokens,
        # otherwise pool is safu.
        pytest.skip("Rebasing token problem")
    for token in pool_tokens + underlying_tokens:
        assert token.balanceOf(charlie) == 0

    # Charlie doesn't have any tokens, all balances are 0
    with boa.reverts():
        swap.exchange(sending, receiving, amount, 0, sender=charlie)


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
