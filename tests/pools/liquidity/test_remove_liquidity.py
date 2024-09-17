import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.parametrize("min_amount", (0, 1))
def test_remove_liquidity(
    alice,
    swap,
    pool_type,
    pool_token_types,
    metapool_token_type,
    pool_tokens,
    underlying_tokens,
    min_amount,
    deposit_amounts,
):
    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]

    amounts_before = [coin.balanceOf(alice) for coin in coins]

    if min_amount == 1 and (  # we specify specify min_amt_out
        (pool_type == 0 and (pool_token_types[0] == 2 or pool_token_types[1] == 2))
        or (pool_type == 1 and metapool_token_type == 2)  # and we have rebasing tokens
    ):
        swap.remove_liquidity(
            swap.balanceOf(alice), [int(0.99 * i * min_amount) for i in deposit_amounts], sender=alice
        )
    else:
        swap.remove_liquidity(swap.balanceOf(alice), [i * min_amount for i in deposit_amounts], sender=alice)

    amounts_after = [coin.balanceOf(alice) for coin in coins]

    for coin, coin_type, amount_before, amount_after in zip(coins, pool_token_types, amounts_before, amounts_after):
        assert amount_after == pytest.approx(
            amount_before * 2, rel=1.5e-2
        )  # we deposit half of all balance value (approx for orcales, rebasing etc)

        if (pool_type == 0 and coin_type == 2) or (pool_type == 1 and metapool_token_type == 2):
            assert coin.balanceOf(swap) == pytest.approx(
                0, abs=(amount_after - amount_before) * (1 - 1000000 / 1000001)  # approx for rebasing tokens
            )
        else:
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
