import boa
import pytest

from tests.fixtures.accounts import add_base_pool_liquidity, mint_account
from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils.tokens import mint_for_testing
from tests.utils.transactions import call_returning_result_and_logs


class TestLiquidityMethods:
    @pytest.mark.usefixtures("initial_setup")
    class TestAddLiquidity:
        def test_add_liquidity(
            self,
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
                        if i == 0:  # up rebasing
                            assert pool_token.balanceOf(bob) >= initial_amounts[i] - deposit_amounts[i]
                            assert pool_token.balanceOf(swap.address) >= deposit_amounts[i] * 2
                        else:  # down rebasing
                            assert pool_token.balanceOf(bob) <= initial_amounts[i] - deposit_amounts[i]
                            assert pool_token.balanceOf(swap.address) <= deposit_amounts[i] * 2
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
            self,
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
                        if i == 0:  # up rebasing
                            assert pool_token.balanceOf(bob) >= initial_amounts[i] - amounts[i] - 1
                            assert pool_token.balanceOf(swap.address) >= deposit_amounts[i] + amounts[i] - 1
                        else:  # down rebasing
                            assert pool_token.balanceOf(bob) <= initial_amounts[i] - amounts[i] + 1
                            assert pool_token.balanceOf(swap.address) <= deposit_amounts[i] + amounts[i] + 1
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

        def test_insufficient_balance(self, charlie, swap, pool_type, decimals, meta_decimals):
            if pool_type == 0:
                amounts = [(10**i) for i in decimals]
            else:
                amounts = [(10**i) for i in [meta_decimals, 18]]

            with boa.reverts():  # invalid approval or balance
                swap.add_liquidity(amounts, 0, sender=charlie)

        def test_min_amount_too_high(self, bob, swap, pool_type, deposit_amounts, pool_tokens):
            size = 2
            if pool_type == 0:
                size = len(pool_tokens)

            with boa.reverts():
                swap.add_liquidity(deposit_amounts, size * INITIAL_AMOUNT // 2 * 10**18 * 101 // 100, sender=bob)

        def test_event(self, bob, swap, pool_type, deposit_amounts, pool_tokens, pool_token_types, metapool_token_type):
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
                    f"invariant={size * INITIAL_AMOUNT * 10**18}, token_supply={swap.totalSupply()})"
                )

        def test_send_eth(self, bob, swap, deposit_amounts):
            with boa.reverts():
                swap.add_liquidity(deposit_amounts, 0, sender=bob, value=1)

    class TestInitialLiquidity:
        @pytest.fixture(scope="module")
        def initial_setup_alice(
            self,
            alice,
            deposit_amounts,
            swap,
            pool_type,
            base_pool,
            base_pool_tokens,
            base_pool_decimals,
            base_pool_lp_token,
            initial_balance,
            initial_amounts,
            pool_tokens,
            underlying_tokens,
        ):
            with boa.env.anchor():
                mint_for_testing(alice, 1 * 10**18, None, True)

                if pool_type == 0:

                    mint_account(alice, pool_tokens, initial_balance, initial_amounts)
                    with boa.env.prank(alice):
                        for token in pool_tokens:
                            token.approve(swap.address, 2**256 - 1)

                else:
                    add_base_pool_liquidity(alice, base_pool, base_pool_tokens, base_pool_decimals)
                    mint_for_testing(alice, initial_amounts[0], underlying_tokens[0], False)

                    with boa.env.prank(alice):
                        for token in underlying_tokens:
                            token.approve(swap.address, 2**256 - 1)

                yield

        @pytest.mark.parametrize("min_amount", [0, 10**18])
        def test_initial(
            self,
            alice,
            initial_setup_alice,
            swap,
            pool_type,
            pool_tokens,
            underlying_tokens,
            pool_token_types,
            metapool_token_type,
            min_amount,
            decimals,
            meta_decimals,
            deposit_amounts,
            initial_amounts,
        ):
            swap.add_liquidity(
                deposit_amounts,
                len(pool_tokens) * min_amount,
                sender=alice,
            )

            token_types = pool_token_types if pool_type == 0 else [metapool_token_type, 18]

            for coin, und_coin, amount, initial, pool_token_type in zip(
                pool_tokens, underlying_tokens, deposit_amounts, initial_amounts, token_types
            ):
                if pool_type == 0:
                    assert coin.balanceOf(alice) == pytest.approx(initial - amount, rel=1.5e-2)
                    assert coin.balanceOf(swap) == pytest.approx(amount, rel=1.5e-2)
                else:
                    assert und_coin.balanceOf(alice) == pytest.approx(initial - amount, rel=1.5e-2)
                    assert und_coin.balanceOf(swap) == pytest.approx(amount, rel=1.5e-2)

        # TODO: boa hangs with it, with added single print it passes
        # @pytest.mark.parametrize("idx", (0, 1))
        # def test_initial_liquidity_missing_coin(
        #     self, alice, initial_setup_alice, swap, pool_type, decimals, meta_decimals, idx
        # ):
        #     swap_decimals = decimals if pool_type == 0 else [meta_decimals, 18]
        #     amounts = [10**i for i in swap_decimals]
        #     amounts[idx] = 0
        #
        #     with boa.reverts():
        #         swap.add_liquidity(amounts, 0, sender=alice)

    @pytest.mark.usefixtures("initial_setup")
    class TestRemoveLiquidity:
        @pytest.mark.parametrize("min_amount", (0, 1))
        def test_remove_liquidity(
            self, alice, swap, pool_type, pool_tokens, underlying_tokens, min_amount, deposit_amounts
        ):
            swap.remove_liquidity(swap.balanceOf(alice), [i * min_amount for i in deposit_amounts], sender=alice)

            coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]

            for coin, amount in zip(coins, deposit_amounts):
                assert coin.balanceOf(alice) == pytest.approx(amount * 2, rel=1.5e-2)
                assert coin.balanceOf(swap) == 0

            assert swap.balanceOf(alice) == 0
            assert swap.totalSupply() == 0

        def test_remove_partial(self, alice, swap, pool_type, pool_tokens, underlying_tokens, pool_size):
            initial_amount = swap.balanceOf(alice)
            withdraw_amount = initial_amount // 2
            coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]
            swap.remove_liquidity(withdraw_amount, [0] * pool_size, sender=alice)

            for coin in coins:
                assert coin.balanceOf(swap) + coin.balanceOf(alice) == pytest.approx(initial_amount, rel=1.5e-2)

            assert swap.balanceOf(alice) == initial_amount - withdraw_amount
            assert swap.totalSupply() == initial_amount - withdraw_amount

        @pytest.mark.parametrize("idx", range(2))
        def test_below_min_amount(self, alice, swap, initial_amounts, idx):
            min_amount = initial_amounts.copy()
            min_amount[idx] += 1

            with boa.reverts():
                swap.remove_liquidity(swap.balanceOf(alice), min_amount, sender=alice)

        def test_amount_exceeds_balance(self, alice, swap, pool_size):
            with boa.reverts():
                swap.remove_liquidity(swap.balanceOf(alice) + 1, [0] * pool_size, sender=alice)

        def test_event(self, alice, bob, swap, pool_type, pool_size):
            swap.transfer(bob, 10**18, sender=alice)
            _, events = call_returning_result_and_logs(
                swap, "remove_liquidity", 10**18, [0] * pool_size, sender=alice
            )

            assert f"RemoveLiquidity(provider={alice}" in repr(events[3])

    @pytest.mark.usefixtures("initial_setup")
    class TestRemoveLiquidityImbalance:
        @pytest.mark.parametrize("divisor", [2, 5, 10])
        def test_remove_balanced(
            self, alice, swap, pool_type, pool_tokens, underlying_tokens, divisor, deposit_amounts, initial_amounts
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
            self,
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

            lp_balance = pool_size * 1_000_000 * 10**18
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
            assert ideal_balance * 0.9994 < actual_balance < ideal_balance

        @pytest.mark.parametrize("divisor", [1, 2, 10])
        def test_exceed_max_burn(self, alice, swap, pool_size, divisor, deposit_amounts):
            amounts = [i // divisor for i in deposit_amounts]
            max_burn = pool_size * 1_000_000 * 10**18 // divisor

            with boa.reverts():
                swap.remove_liquidity_imbalance(amounts, max_burn - 1, sender=alice)

        def test_cannot_remove_zero(self, alice, swap, pool_size):
            with boa.reverts():
                swap.remove_liquidity_imbalance([0] * pool_size, 0, sender=alice)

        def test_no_totalsupply(self, alice, swap, pool_size):
            swap.remove_liquidity(swap.totalSupply(), [0] * pool_size, sender=alice)
            with boa.reverts():
                swap.remove_liquidity_imbalance([0] * pool_size, 0, sender=alice)

        def test_event(self, alice, bob, swap, pool_type, pool_size, deposit_amounts):
            swap.transfer(bob, swap.balanceOf(alice), sender=alice)
            amounts = [i // 5 for i in deposit_amounts]
            max_burn = pool_size * 1_000_000 * 10**18

            _, events = call_returning_result_and_logs(
                swap, "remove_liquidity_imbalance", amounts, max_burn, sender=bob
            )

            assert f"RemoveLiquidityImbalance(provider={bob}" in repr(events[3])

    @pytest.mark.usefixtures("initial_setup")
    class TestRemoveLiquidityOneCoin:
        @pytest.mark.parametrize("idx", range(2))
        def test_amount_received(self, alice, swap, pool_type, pool_tokens, underlying_tokens, decimals, idx):
            coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]
            initial_amount = coins[idx].balanceOf(alice)

            swap.remove_liquidity_one_coin(10**18, idx, 0, sender=alice)
            ideal = 10 ** decimals[idx]
            assert ideal * 0.99 <= coins[idx].balanceOf(alice) - initial_amount <= ideal

        @pytest.mark.parametrize("idx", range(2))
        @pytest.mark.parametrize("divisor", [1, 5, 42])
        def test_lp_token_balance(self, alice, swap, idx, divisor):
            initial_amount = swap.balanceOf(alice)
            amount = initial_amount // divisor

            swap.remove_liquidity_one_coin(amount, idx, 0, sender=alice)

            assert swap.balanceOf(alice) + amount == initial_amount

        @pytest.mark.parametrize("idx", range(2))
        def test_expected_vs_actual(self, alice, swap, pool_type, pool_tokens, underlying_tokens, idx):
            coins = pool_tokens if pool_type == 0 else underlying_tokens[:2]
            initial_amount = coins[idx].balanceOf(alice)
            amount = swap.balanceOf(alice) // 10

            expected = swap.calc_withdraw_one_coin(amount, idx)
            swap.remove_liquidity_one_coin(amount, idx, 0, sender=alice)
            assert coins[idx].balanceOf(alice) == expected + initial_amount

        @pytest.mark.parametrize("idx", range(2))
        def test_below_min_amount(self, alice, swap, idx):
            amount = swap.balanceOf(alice)

            expected = swap.calc_withdraw_one_coin(amount, idx)
            with boa.reverts():
                swap.remove_liquidity_one_coin(amount, idx, expected + 1, sender=alice)

        @pytest.mark.parametrize("idx", range(2))
        def test_amount_exceeds_balance(self, bob, swap, idx):
            with boa.reverts():
                swap.remove_liquidity_one_coin(1, idx, 0, sender=bob)

        # TODO: this hangs
        # def test_below_zero(self, alice, swap):
        #     with boa.reverts():
        #         swap.remove_liquidity_one_coin(1, -1, 0, sender=alice)

        # TODO: this hangs
        # def test_above_n_coins(self, alice, swap, pool_size):
        #     with boa.reverts():
        #         swap.remove_liquidity_one_coin(1, pool_size, 0, sender=alice)

        @pytest.mark.parametrize("idx", range(2))
        def test_event(self, alice, bob, swap, idx, pool_type):
            swap.transfer(bob, 10**18, sender=alice)
            _, events = call_returning_result_and_logs(swap, "remove_liquidity_one_coin", 10**18, idx, 0, sender=bob)

            if pool_type == 0:
                assert f"RemoveLiquidityOne(provider={bob}" in repr(events[2])
            else:
                assert f"RemoveLiquidityOne(provider={bob}" in repr(events[3])
