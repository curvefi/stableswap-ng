import boa
import pytest

from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils.transactions import call_returning_result_and_logs

pytestmark = pytest.mark.usefixtures("initial_setup")


def test_add_liquidity(
    bob,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    deposit_amounts,
    initial_amounts,
    pool_token_types,
    metapool_token_type,
):
    swap.add_liquidity(deposit_amounts, 0, sender=bob)
    is_ideal = True

    if pool_type == 0:
        for i, (pool_token, amount) in enumerate(zip(pool_tokens, deposit_amounts)):
            if pool_token_types[i] == 2:
                is_ideal = False
                assert pool_token.balanceOf(bob) >= initial_amounts[i] - deposit_amounts[i]
                assert pool_token.balanceOf(swap.address) >= deposit_amounts[i] * 2
            else:
                assert pool_token.balanceOf(bob) == initial_amounts[i] - deposit_amounts[i]
                assert pool_token.balanceOf(swap.address) == deposit_amounts[i] * 2

                if pool_token_types[i] == 1:
                    is_ideal = False

        ideal = len(pool_tokens) * INITIAL_AMOUNT // 2 * 10**18
        if is_ideal:
            assert abs(swap.balanceOf(bob) - ideal) <= 1
            assert abs(swap.totalSupply() - ideal * 2) <= 2
    else:
        if metapool_token_type == 2:
            assert underlying_tokens[0].balanceOf(bob) >= initial_amounts[0] - deposit_amounts[0]
            assert underlying_tokens[0].balanceOf(swap.address) >= deposit_amounts[0] * 2
        else:
            assert underlying_tokens[0].balanceOf(bob) == initial_amounts[0] - deposit_amounts[0]
            assert underlying_tokens[0].balanceOf(swap.address) == deposit_amounts[0] * 2

            if metapool_token_type == 0:
                ideal = INITIAL_AMOUNT * 10**18  # // 2 * 2
                assert abs(swap.balanceOf(bob) - ideal) <= 1
                assert abs(swap.totalSupply() - ideal * 2) <= 2

        assert underlying_tokens[1].balanceOf(bob) == initial_amounts[1] - deposit_amounts[1]
        assert underlying_tokens[1].balanceOf(swap) == deposit_amounts[1] * 2


@pytest.mark.parametrize("idx", (0, 1))
def test_add_one_coin(
    bob,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    deposit_amounts,
    initial_amounts,
    pool_token_types,
    metapool_token_type,
    idx,
):
    amounts = [0] * len(pool_tokens)
    amounts[idx] = deposit_amounts[idx]

    swap.add_liquidity(amounts, 0, sender=bob)
    is_ideal = True

    if pool_type == 0:
        for i, pool_token in enumerate(pool_tokens):
            if pool_token_types[i] == 2:
                is_ideal = False
                assert pool_token.balanceOf(bob) >= initial_amounts[i] - amounts[i] - 1
                assert pool_token.balanceOf(swap.address) >= deposit_amounts[i] + amounts[i] - 1
            else:
                assert pool_token.balanceOf(bob) == initial_amounts[i] - amounts[i]
                assert pool_token.balanceOf(swap.address) == deposit_amounts[i] + amounts[i]
    else:
        if metapool_token_type == 2:
            is_ideal = False
            assert underlying_tokens[0].balanceOf(bob) >= initial_amounts[0] - amounts[0] - 1
            assert underlying_tokens[0].balanceOf(swap.address) >= deposit_amounts[0] + amounts[0] - 1
        else:
            assert underlying_tokens[0].balanceOf(bob) == initial_amounts[0] - amounts[0]
            assert underlying_tokens[0].balanceOf(swap) == deposit_amounts[0] + amounts[0]

        assert underlying_tokens[1].balanceOf(bob) == initial_amounts[1] - amounts[1]
        assert underlying_tokens[1].balanceOf(swap) == deposit_amounts[1] + amounts[1]

    difference = abs(swap.balanceOf(bob) - deposit_amounts[idx])
    if is_ideal:
        assert difference / (deposit_amounts[idx]) < 0.01
    else:
        assert difference / (deposit_amounts[idx]) < 0.02


def test_insufficient_balance(charlie, swap, pool_type, decimals, meta_decimals):
    if pool_type == 0:
        amounts = [(10**i) for i in decimals]
    else:
        amounts = [(10**i) for i in [meta_decimals, 18]]

    with boa.reverts():  # invalid approval or balance
        swap.add_liquidity(amounts, 0, sender=charlie)


def test_min_amount_too_high(bob, swap, pool_type, deposit_amounts, pool_tokens):
    size = 2
    if pool_type == 0:
        size = len(pool_tokens)

    with boa.reverts():
        swap.add_liquidity(deposit_amounts, size * INITIAL_AMOUNT // 2 * 10**18 * 101 // 100, sender=bob)


def test_event(bob, swap, pool_type, deposit_amounts, pool_tokens, pool_token_types, metapool_token_type):
    size = 2
    check_invariant = True
    if pool_type == 0:
        size = len(pool_tokens)

        for t in pool_token_types:
            if t != 0:
                check_invariant = False

    if pool_type == 1:
        if metapool_token_type != 0:
            check_invariant = False

    _, events = call_returning_result_and_logs(swap, "add_liquidity", deposit_amounts, 0, sender=bob)

    assert len(events) == 4  # Transfer token1, Transfer token2, Transfer LP, Add liquidity
    if check_invariant:
        assert (
            repr(events[3]) == f"AddLiquidity(provider={bob}, token_amounts={deposit_amounts}, fees=[0, 0], "
            f"invariant={size * INITIAL_AMOUNT * 10 ** 18}, token_supply={swap.totalSupply()})"
        )


def test_send_eth(bob, swap, deposit_amounts):
    with boa.reverts():
        swap.add_liquidity(deposit_amounts, 0, sender=bob, value=1)
