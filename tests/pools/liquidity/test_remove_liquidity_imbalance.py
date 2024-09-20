import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.parametrize("divisor", [2, 5, 10])
def test_remove_balanced(
    alice,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    divisor,
    deposit_amounts,
    initial_amounts,
):
    initial_balance = swap.balanceOf(alice)
    amounts = [i // divisor for i in deposit_amounts]
    swap.remove_liquidity_imbalance(amounts, initial_balance, sender=alice)

    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]

    for i, coin in enumerate(coins):
        assert coin.balanceOf(alice) == pytest.approx(
            amounts[i] + initial_amounts[i] - deposit_amounts[i], rel=1.5e-2
        )
        assert coin.balanceOf(swap) == pytest.approx(deposit_amounts[i] - amounts[i], rel=1.5e-2)

    assert swap.balanceOf(alice) / initial_balance == pytest.approx(1 - 1 / divisor, rel=1.5e-2)


@pytest.mark.parametrize("idx", range(2))
def test_remove_one(
    alice,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    pool_size,
    idx,
    deposit_amounts,
    initial_amounts,
):
    amounts = [0] * pool_size
    amounts[idx] = deposit_amounts[idx] // 2

    lp_balance = pool_size * deposit_amounts[idx]
    swap.remove_liquidity_imbalance(amounts, lp_balance, sender=alice)

    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]

    for i, coin in enumerate(coins):
        assert coin.balanceOf(alice) == pytest.approx(
            amounts[i] + initial_amounts[i] - deposit_amounts[i], rel=1.5e-2
        )
        assert coin.balanceOf(swap) == pytest.approx(deposit_amounts[i] - amounts[i], rel=1.5e-2)

    actual_balance = swap.balanceOf(alice)
    actual_total_supply = swap.totalSupply()
    ideal_balance = (2 * pool_size - 1) * lp_balance / (2 * pool_size)

    assert actual_balance == actual_total_supply
    assert ideal_balance * 0.9994 < actual_balance
    assert actual_balance < ideal_balance * 1.07


@pytest.mark.parametrize("divisor", [1, 2, 10])
def test_exceed_max_burn(alice, swap, pool_size, divisor, deposit_amounts):
    amounts = [i // divisor for i in deposit_amounts]
    max_burn = pool_size * 1_000_000 * 10**18 // divisor

    with boa.reverts():
        swap.remove_liquidity_imbalance(amounts, max_burn - 1, sender=alice)


def test_cannot_remove_zero(alice, swap, pool_size):
    with boa.reverts():
        swap.remove_liquidity_imbalance([0] * pool_size, 0, sender=alice)


def test_no_total_supply(alice, swap, pool_size):
    swap.remove_liquidity(swap.totalSupply(), [0] * pool_size, sender=alice)
    with boa.reverts():
        swap.remove_liquidity_imbalance([0] * pool_size, 0, sender=alice)


def test_event(alice, bob, swap, pool_size, deposit_amounts):
    swap.transfer(bob, swap.balanceOf(alice), sender=alice)
    amounts = [i // 5 for i in deposit_amounts]
    max_burn = pool_size * 1_000_000 * 10**18

    _, events = call_returning_result_and_logs(
        swap, "remove_liquidity_imbalance", amounts, max_burn, sender=bob
    )

    assert f"RemoveLiquidityImbalance(provider={bob}" in repr(events[3])
