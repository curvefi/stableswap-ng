import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


def test_add_liquidity(bob, charlie, swap, deposit_amounts):
    swap.add_liquidity(deposit_amounts, 0, charlie, sender=bob)

    assert swap.balanceOf(bob) == 0
    assert swap.balanceOf(charlie) > 0


def test_exchange(
    bob, charlie, swap, pool_type, pool_tokens, underlying_tokens, decimals, pool_token_types, metapool_token_type
):
    balance = pool_tokens[0].balanceOf(bob) if pool_type == 0 else underlying_tokens[0].balanceOf(bob)

    swap.exchange(1, 0, 1000 * 10**18, 0, charlie, sender=bob)
    if pool_type == 0:
        assert pool_tokens[0].balanceOf(charlie) > 0
        if pool_token_types[0] != 2:
            assert pool_tokens[0].balanceOf(bob) == balance
        else:
            assert pool_tokens[0].balanceOf(bob) == pytest.approx(balance, rel=2e-2)
    else:
        assert underlying_tokens[0].balanceOf(charlie) > 0
        if metapool_token_type != 2:
            assert underlying_tokens[0].balanceOf(bob) == balance
        else:
            assert underlying_tokens[0].balanceOf(bob) == pytest.approx(balance, rel=2e-2)


def test_remove_liquidity(
    bob, swap, charlie, pool_type, pool_tokens, underlying_tokens, initial_amounts, pool_size, deposit_amounts
):
    swap.add_liquidity(deposit_amounts, 0, sender=bob)
    initial_amount = swap.balanceOf(bob)
    withdraw_amount = initial_amount // 4
    swap.remove_liquidity(withdraw_amount, [0] * pool_size, charlie, sender=bob)

    i = 0
    if pool_type == 0:
        for coin, amount in zip(pool_tokens, deposit_amounts):
            assert coin.balanceOf(swap) + coin.balanceOf(charlie) == pytest.approx(deposit_amounts[0] * 2, rel=1.5e-2)
            i += 1
    else:
        for coin, amount in zip(underlying_tokens[:2], deposit_amounts):
            assert coin.balanceOf(swap) + coin.balanceOf(charlie) == pytest.approx(deposit_amounts[0] * 2, rel=1.5e-2)
            i += 1

    assert swap.balanceOf(bob) == pytest.approx(deposit_amounts[0] * pool_size - withdraw_amount, rel=1.5e-2)
    assert swap.totalSupply() == pytest.approx(deposit_amounts[0] * 2 * pool_size - withdraw_amount, rel=1.5e-2)


def test_remove_imbalanced(
    bob, swap, charlie, pool_type, pool_tokens, underlying_tokens, initial_amounts, deposit_amounts
):
    swap.add_liquidity(deposit_amounts, 0, sender=bob)
    balance = swap.balanceOf(bob)
    amounts = [i // 4 for i in initial_amounts]
    swap.remove_liquidity_imbalance(amounts, balance, charlie, sender=bob)

    if pool_type == 0:
        for i, coin in enumerate(pool_tokens):
            assert coin.balanceOf(charlie) == pytest.approx(amounts[i], rel=1.5e-2)
            assert coin.balanceOf(swap) == pytest.approx(initial_amounts[i] - amounts[i], rel=1.5e-2)
    else:
        for i, coin in enumerate(underlying_tokens[:2]):
            assert coin.balanceOf(charlie) == pytest.approx(amounts[i], rel=1.5e-2)
            assert coin.balanceOf(swap) == pytest.approx(initial_amounts[i] - amounts[i], rel=1.5e-2)

    assert swap.balanceOf(bob) / balance == pytest.approx(0.5, rel=1.5e-2)


def test_remove_one_coin(alice, charlie, swap, pool_tokens, underlying_tokens):
    swap.remove_liquidity_one_coin(10**18, 0, 0, charlie, sender=alice)

    assert swap.balanceOf(charlie) == 0
    assert swap.balanceOf(alice) > 0
