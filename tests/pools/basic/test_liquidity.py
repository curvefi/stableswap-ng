import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs

DEPOSIT_AMOUNT = 500_000


class TestLiquidityMethods:
    @pytest.mark.usefixtures("add_initial_liquidity_alice", "mint_bob", "approve_bob")
    class TestAddLiquidity:
        @pytest.mark.parametrize("use_eth", (True, False), scope="session")
        def test_add_liquidity(
            self, bob, swap, is_eth_pool, pool_tokens, deposit_amounts, initial_balance, initial_amounts, use_eth
        ):
            value = deposit_amounts[0] if is_eth_pool and use_eth else 0
            deposit_amounts[0] = 0 if is_eth_pool and use_eth else deposit_amounts[0]
            swap.add_liquidity(deposit_amounts, 0, use_eth, sender=bob, value=value)

            for i, (pool_token, amount) in enumerate(zip(pool_tokens, deposit_amounts)):
                assert pool_token.balanceOf(bob) == initial_amounts[i] - deposit_amounts[i]
                assert pool_token.balanceOf(swap.address) == deposit_amounts[i] * 2

            ideal = len(pool_tokens) * DEPOSIT_AMOUNT * 10**18
            assert abs(swap.balanceOf(bob) - ideal) <= 1
            assert abs(swap.totalSupply() - ideal * 2) <= 2

        @pytest.mark.parametrize("idx", (0, 1))
        @pytest.mark.parametrize("use_eth", (True, False))
        def test_add_one_coin(
            self, bob, swap, pool_tokens, is_eth_pool, deposit_amounts, initial_amounts, idx, weth, use_eth
        ):
            amounts = [0] * len(pool_tokens)
            amounts[idx] = deposit_amounts[idx]

            swap.add_liquidity(amounts, 0, sender=bob)

            for i, pool_token in enumerate(pool_tokens):
                if pool_token == weth:
                    assert boa.env.get_balance(bob) == initial_amounts[i] - amounts[i]
                    assert boa.env.get_balance(swap) == deposit_amounts[i] + amounts[i]
                else:
                    assert pool_token.balanceOf(bob) == initial_amounts[i] - amounts[i]
                    assert pool_token.balanceOf(swap) == deposit_amounts[i] + amounts[i]

            difference = abs(swap.balanceOf(bob) - (10**18 * DEPOSIT_AMOUNT))
            assert difference / (10**18 * DEPOSIT_AMOUNT) < 0.01

        def test_insufficient_balance(self, charlie, swap, decimals):
            amounts = [(10**i) for i in decimals]

            with boa.reverts():  # invalid approval or balance
                swap.add_liquidity(amounts, 0, sender=charlie)

        def test_min_amount_too_high(self, bob, swap, deposit_amounts, pool_size):
            with boa.reverts():
                swap.add_liquidity(deposit_amounts, pool_size * DEPOSIT_AMOUNT * 10**18 + 1, sender=bob)

        def test_event(self, bob, swap, deposit_amounts):
            _, events = call_returning_result_and_logs(swap, "add_liquidity", deposit_amounts, 0, sender=bob)

            assert len(events) == 4  # Transfer token1, Transfer token2, Transfer LP, Add liquidity
            assert (
                repr(events[3]) == f"AddLiquidity(provider={bob}, token_amounts={deposit_amounts}, fees=[0, 0], "
                f"invariant={2_000_000 * 10 ** 18}, token_supply={swap.totalSupply()})"
            )

        # TODO: fix this
        #
        # def test_send_eth(self, bob, swap, deposit_amounts, use_eth):
        #
        #     # with boa.reverts():
        #     swap.add_liquidity(deposit_amounts, 0, True, sender=bob, value=1)
