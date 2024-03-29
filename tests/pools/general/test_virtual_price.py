import pytest

from tests.utils.tokens import mint_for_testing

pytestmark = pytest.mark.usefixtures("initial_setup")


def test_number_go_up(bob, swap, initial_amounts, pool_size):
    virtual_price = swap.get_virtual_price()

    for i, amount in enumerate(initial_amounts):
        amounts = [0] * pool_size
        amounts[i] = amount
        swap.add_liquidity(amounts, 0, sender=bob)

        new_virtual_price = swap.get_virtual_price()
        assert new_virtual_price > virtual_price
        virtual_price = new_virtual_price


@pytest.mark.parametrize("idx", range(2))
def test_remove_one_coin(alice, swap, idx):
    amount = swap.balanceOf(alice) // 10

    virtual_price = swap.get_virtual_price()
    swap.remove_liquidity_one_coin(amount, idx, 0, sender=alice)

    assert swap.get_virtual_price() > virtual_price


@pytest.mark.parametrize("idx", range(2))
def test_remove_imbalance(alice, swap, idx, deposit_amounts, pool_size):
    amounts = [i // 2 for i in deposit_amounts]
    amounts[idx] = 0

    virtual_price = swap.get_virtual_price()
    swap.remove_liquidity_imbalance(amounts, pool_size * 1_000_000 * 10**18, sender=alice)

    assert swap.get_virtual_price() > virtual_price


def test_remove(alice, swap, pool_size, deposit_amounts):
    withdraw_amount = sum(deposit_amounts) // 2

    virtual_price = swap.get_virtual_price()
    swap.remove_liquidity(withdraw_amount, [0] * pool_size, sender=alice)

    assert swap.get_virtual_price() >= virtual_price


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange(bob, swap, sending, receiving, decimals):
    virtual_price = swap.get_virtual_price()

    amount = 10_000 * 10 ** decimals[sending]
    swap.exchange(sending, receiving, amount, 0, sender=bob)

    assert swap.get_virtual_price() > virtual_price


def test_donate_virtual_price(bob, swap, pool_tokens, initial_amounts, pool_size):
    # make a deposit
    for i, amount in enumerate(initial_amounts):
        amounts = [0] * pool_size
        amounts[i] = amount
        swap.add_liquidity(amounts, 0, sender=bob)

    virtual_price_pre_donation = swap.get_virtual_price()

    # airdrop some tokens to increase the price.
    pool_balances_post_donation = []
    for i, token in enumerate(pool_tokens):
        to_deposit = token.balanceOf(swap)
        mint_for_testing(swap.address, to_deposit, token, False)  # directly mint to pool
        pool_balances_post_donation.append(token.balanceOf(swap))

    virtual_price_post_donation = swap.get_virtual_price()
    assert virtual_price_pre_donation == virtual_price_post_donation

    # remove liquidity in one coin.
    swap.remove_liquidity_one_coin(swap.balanceOf(bob), 0, 0, sender=bob)
    virtual_price_post_withdrawal = swap.get_virtual_price()

    assert virtual_price_post_withdrawal < 1.05 * virtual_price_post_donation
