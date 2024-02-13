import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.parametrize("min_amount", (0, 1))
def test_remove_liquidity(alice, swap, pool_type, pool_tokens, underlying_tokens, min_amount, deposit_amounts):
    swap.remove_liquidity(swap.balanceOf(alice), [i * min_amount for i in deposit_amounts], sender=alice)

    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]

    for coin, amount in zip(coins, deposit_amounts):
        assert coin.balanceOf(alice) == pytest.approx(amount * 2, rel=1.5e-2)
        assert coin.balanceOf(swap) == 0

    assert swap.balanceOf(alice) == 0
    assert swap.totalSupply() == 0


def test_remove_partial(alice, swap, pool_type, pool_tokens, underlying_tokens, pool_size):
    initial_amount = swap.balanceOf(alice)
    withdraw_amount = initial_amount // 2
    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]
    swap.remove_liquidity(withdraw_amount, [0] * pool_size, sender=alice)

    for coin in coins:
        assert coin.balanceOf(swap) + coin.balanceOf(alice) == pytest.approx(initial_amount, rel=1.5e-2)

    assert swap.balanceOf(alice) == initial_amount - withdraw_amount
    assert swap.totalSupply() == initial_amount - withdraw_amount


@pytest.mark.parametrize("idx", range(2))
def test_below_min_amount(alice, swap, initial_amounts, idx):
    min_amount = initial_amounts.copy()
    min_amount[idx] += 1

    with boa.reverts():
        swap.remove_liquidity(swap.balanceOf(alice), min_amount, sender=alice)


def test_amount_exceeds_balance(alice, swap, pool_size):
    with boa.reverts():
        swap.remove_liquidity(swap.balanceOf(alice) + 1, [0] * pool_size, sender=alice)


def test_event(alice, bob, swap, pool_size):
    swap.transfer(bob, 10**18, sender=alice)
    _, events = call_returning_result_and_logs(swap, "remove_liquidity", 10**18, [0] * pool_size, sender=alice)

    assert f"RemoveLiquidity(provider={alice}" in repr(events[3])
