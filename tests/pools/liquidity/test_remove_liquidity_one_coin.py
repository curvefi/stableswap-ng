import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.parametrize("idx", range(2))
def test_amount_received(
    alice,
    swap,
    pool_type,
    pool_tokens,
    pool_token_types,
    metapool_token_type,
    underlying_tokens,
    decimals,
    idx,
):
    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]
    initial_amount = coins[idx].balanceOf(alice)
    # if pool_token_types[0] == pool_token_types[1] == 2:
    #     pass
    swap.remove_liquidity_one_coin(10**18, idx, 0, sender=alice)
    if (pool_type == 0 and pool_token_types[idx] == 2) or (  # rebase token in base pool
        pool_type == 1 and metapool_token_type == 2 and idx == 0  # rebase token in metapool
    ):
        ideal = 2.5 * 10 ** decimals[idx]  # rebasing tokens got inflated (2.5e18 for two transfers)
    else:
        ideal = 10 ** decimals[idx]
    assert ideal * 0.99 <= coins[idx].balanceOf(alice) - initial_amount <= ideal


@pytest.mark.parametrize("idx", range(2))
@pytest.mark.parametrize("divisor", [1, 5, 42])
def test_lp_token_balance(alice, swap, idx, divisor):
    initial_amount = swap.balanceOf(alice)
    amount = initial_amount // divisor

    if divisor == 1:
        with boa.reverts():
            swap.remove_liquidity_one_coin(amount, idx, 0, sender=alice)
    else:
        swap.remove_liquidity_one_coin(amount, idx, 0, sender=alice)

        assert swap.balanceOf(alice) + amount == initial_amount


@pytest.mark.parametrize("idx", range(2))
def test_expected_vs_actual(
    alice,
    swap,
    pool_type,
    pool_tokens,
    pool_token_types,
    metapool_token_type,
    underlying_tokens,
    idx,
):
    coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]
    initial_amount = coins[idx].balanceOf(alice)
    amount = swap.balanceOf(alice) // 10

    expected = swap.calc_withdraw_one_coin(amount, idx)
    swap.remove_liquidity_one_coin(amount, idx, 0, sender=alice)
    if (pool_type == 0 and pool_token_types[idx] == 2) or (  # rebase token in base pool
        pool_type == 1 and metapool_token_type == 2 and idx == 0  # rebase token in metapool
    ):
        delta = 1.51 * 10**18  # single transfer rebasing (hardcoded for fixed amounts)
    else:
        delta = 0

    assert coins[idx].balanceOf(alice) == pytest.approx(expected + initial_amount, abs=delta)


@pytest.mark.parametrize("idx", range(2))
def test_below_min_amount(alice, swap, idx):
    amount = swap.balanceOf(alice)

    expected = swap.calc_withdraw_one_coin(amount, idx)
    with boa.reverts():
        swap.remove_liquidity_one_coin(amount, idx, expected + 1, sender=alice)


@pytest.mark.parametrize("idx", range(2))
def test_amount_exceeds_balance(bob, swap, idx):
    with boa.reverts():
        swap.remove_liquidity_one_coin(1, idx, 0, sender=bob)


def test_below_zero(alice, swap):
    with boa.reverts():
        swap.remove_liquidity_one_coin(1, -1, 0, sender=alice)


def test_above_n_coins(alice, swap, pool_size):
    with boa.reverts():
        swap.remove_liquidity_one_coin(1, pool_size, 0, sender=alice)


@pytest.mark.parametrize("idx", range(2))
def test_event(alice, bob, swap, idx):
    swap.transfer(bob, 10**18, sender=alice)
    _, events = call_returning_result_and_logs(
        swap, "remove_liquidity_one_coin", 10**18, idx, 0, sender=bob
    )
    assert f"RemoveLiquidityOne(provider={bob}" in repr(events[2])
