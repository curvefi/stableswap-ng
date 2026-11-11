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


def _start_rewards(owner, gauge, coins, amount=REWARD):
    with boa.env.prank(owner):
        for coin in coins:
            gauge.add_reward(coin.address, owner)
            coin._mint_for_testing(owner, amount)
            coin.approve(gauge.address, amount)
            gauge.deposit_reward_token(coin.address, amount)
    boa.env.time_travel(seconds=WEEK)


def test_deposit_reward_token_cap(owner, coin_reward, gauge):
    amount = 2**96 + 1
    with boa.env.prank(owner):
        gauge.add_reward(coin_reward.address, owner)
        coin_reward._mint_for_testing(owner, 2 * amount)
        coin_reward.approve(gauge.address, 2 * amount)
        with boa.reverts("Reward overflow"):
            gauge.deposit_reward_token(coin_reward.address, amount)

        gauge.deposit_reward_token(coin_reward.address, 2**96)
        # the leftover of the running period counts towards the cap
        with boa.reverts("Reward overflow"):
            gauge.deposit_reward_token(coin_reward.address, 2**95)


def test_claim_selected_rewards(owner, coin_reward, coin_reward_b, gauge):
    _start_rewards(owner, gauge, [coin_reward, coin_reward_b])
    balances = [coin_reward.balanceOf(owner), coin_reward_b.balanceOf(owner)]

    with boa.env.prank(owner):
        gauge.claim_rewards(owner, boa.eval("empty(address)"), [coin_reward.address])

    claimed = coin_reward.balanceOf(owner) - balances[0]
    assert claimed > 0
    assert gauge.claimed_reward(owner, coin_reward.address) == claimed
    # the reward that was not listed stays pending
    assert coin_reward_b.balanceOf(owner) == balances[1]
    assert gauge.claimable_reward(owner, coin_reward_b.address) == claimed

    with boa.env.prank(owner):
        gauge.claim_rewards()
    assert coin_reward_b.balanceOf(owner) - balances[1] == claimed
    assert gauge.claimable_reward(owner, coin_reward_b.address) == 0


def test_set_reward_invalidated_access(owner, factory, coin_reward, coin_reward_b, gauge):
    non_owner = boa.env.generate_address("non_owner")
    with boa.env.prank(owner):
        gauge.add_reward(coin_reward.address, owner)

    with boa.env.prank(non_owner), boa.reverts():
        gauge.set_reward_invalidated(coin_reward.address, True)
    with boa.env.prank(owner), boa.reverts():
        gauge.set_reward_invalidated(coin_reward_b.address, True)  # not a reward

    with boa.env.prank(gauge.manager()):
        gauge.set_reward_invalidated(coin_reward.address, True)
    assert gauge.invalidated_reward(coin_reward.address)
    with boa.env.prank(factory.admin()):
        gauge.set_reward_invalidated(coin_reward.address, False)
    assert not gauge.invalidated_reward(coin_reward.address)


def test_invalidated_reward_skipped_by_default(owner, coin_reward, coin_reward_b, gauge):
    _start_rewards(owner, gauge, [coin_reward, coin_reward_b])
    balances = [coin_reward.balanceOf(owner), coin_reward_b.balanceOf(owner)]

    with boa.env.prank(owner):
        gauge.set_reward_invalidated(coin_reward.address, True)
        gauge.claim_rewards()
        gauge.withdraw(LP_AMOUNT // 2, True)

    # only the valid reward is transferred, the invalidated one keeps accruing
    assert coin_reward.balanceOf(owner) == balances[0]
    pending = gauge.claimable_reward(owner, coin_reward.address)
    assert pending > 0
    assert coin_reward_b.balanceOf(owner) - balances[1] == pending

    # still claimable explicitly
    with boa.env.prank(owner):
        gauge.claim_rewards(owner, boa.eval("empty(address)"), [coin_reward.address])
    assert coin_reward.balanceOf(owner) - balances[0] == pending

    # and by default again once the flag is cleared
    with boa.env.prank(owner):
        coin_reward._mint_for_testing(owner, REWARD)
        coin_reward.approve(gauge.address, REWARD)
        gauge.deposit_reward_token(coin_reward.address, REWARD)
    boa.env.time_travel(seconds=WEEK)
    with boa.env.prank(owner):
        gauge.set_reward_invalidated(coin_reward.address, False)
        gauge.claim_rewards()
    assert coin_reward.balanceOf(owner) - balances[0] > pending
