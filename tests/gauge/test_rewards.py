import boa
import pytest

REWARD = 10**20
WEEK = 7 * 86400
LP_AMOUNT = 10**18


@pytest.fixture(autouse=True)
def initial_setup(forked_chain, factory, owner, gauge, swap, add_initial_liquidity_owner):
    with boa.env.prank(owner):
        swap.approve(gauge.address, LP_AMOUNT)
        gauge.deposit(LP_AMOUNT)


def test_set_rewards_no_deposit(owner, coin_reward, swap, gauge, zero_address):
    with boa.env.prank(owner):
        gauge.add_reward(coin_reward.address, owner)

    assert swap.balanceOf(gauge.address) == LP_AMOUNT
    assert gauge.reward_tokens(0) == coin_reward.address
    assert gauge.reward_tokens(1) == zero_address


def test_multiple_reward_tokens(owner, coin_reward, coin_reward_a, coin_reward_b, gauge):
    coins = [coin_reward.address, coin_reward_a.address, coin_reward_b.address]
    with boa.env.prank(owner):
        for coin in coins:
            gauge.add_reward(coin, owner)

    assert coins == [gauge.reward_tokens(i) for i in range(3)]


def test_cant_exceed_max(owner, coin_rewards_additional, gauge):
    with boa.env.prank(owner):
        for i in range(8):
            gauge.add_reward(coin_rewards_additional[i].address, owner)
        with boa.reverts():
            gauge.add_reward(coin_rewards_additional[i].address, owner)
