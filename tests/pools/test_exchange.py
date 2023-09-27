import boa
import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


class TestExchange:
    @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
    def test_min_dy(
        self,
        bob,
        swap,
        pool_type,
        pool_tokens,
        underlying_tokens,
        pool_token_types,
        metapool_token_type,
        sending,
        receiving,
        decimals,
    ):
        amount = 1000 * 10 ** decimals[sending]
        initial_receiving = (
            pool_tokens[receiving].balanceOf(bob) if pool_type == 0 else underlying_tokens[receiving].balanceOf(bob)
        )

        min_dy = swap.get_dy(sending, receiving, amount)
        # apply rebasing for expected dy
        # Down rebasing breaks dy
        if pool_type == 0 and pool_token_types[sending] == 2 and sending == 1:
            min_dy -= pool_tokens[sending].balanceOf(swap.address) // 1000000

        swap.exchange(sending, receiving, amount, min_dy - 1, sender=bob)

        if pool_type == 0:
            received = pool_tokens[receiving].balanceOf(bob)
        else:
            received = underlying_tokens[receiving].balanceOf(bob)

        if (pool_type == 0 and 2 in pool_token_types) or (pool_type == 1 and metapool_token_type == 2):
            assert abs(received - min_dy - initial_receiving) == pytest.approx(1, abs=received // 1000000)
        else:
            assert abs(received - min_dy - initial_receiving) <= 1

    @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
    def test_min_dy_imbalanced(
        self,
        bob,
        swap,
        pool_type,
        pool_tokens,
        underlying_tokens,
        pool_token_types,
        metapool_token_type,
        sending,
        receiving,
        decimals,
    ):
        amounts = [1_500_000 * 10**i for i in decimals]
        scaler = amounts.copy()  # used to scale token amounts when decimals are different

        amounts[sending] = 0
        amounts[receiving] = amounts[receiving]

        swap.add_liquidity(amounts, 0, sender=bob)

        # oracle
        rate = 1
        if pool_type == 0:
            if pool_token_types[sending] == 1:
                rate = rate / (pool_tokens[sending].exchangeRate() / 10**18)
            if pool_token_types[receiving] == 1:
                rate = rate * (pool_tokens[receiving].exchangeRate() / 10**18)

        elif pool_type == 1:
            if metapool_token_type == 1:
                if sending == 0:
                    rate = rate / (underlying_tokens[0].exchangeRate() / 10**18)

                if receiving == 0:
                    rate = rate * (underlying_tokens[0].exchangeRate() / 10**18)

        # we need to scale these appropriately for tokens with different decimal values
        min_dy_sending = swap.get_dy(sending, receiving, scaler[sending]) / scaler[receiving]
        min_dy_receiving = swap.get_dy(receiving, sending, scaler[receiving]) / scaler[sending]

        assert min_dy_sending * rate > min_dy_receiving

    class TestExchangeReverts:
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_insufficient_balance(
            self, charlie, pool_tokens, underlying_tokens, swap, sending, receiving, decimals
        ):

            amount = 10 ** decimals[sending]

            for token in pool_tokens + underlying_tokens:
                assert token.balanceOf(charlie) == 0

            # Charlie doesn't have any tokens, all balances are 0
            try:
                swap.exchange(sending, receiving, amount + 1, 0, sender=charlie)
                assert False
            except:  # noqa: E722
                assert True

        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        @pytest.mark.contains_rebasing_tokens
        def test_zero_amount_swap(self, charlie, pool_tokens, underlying_tokens, swap, sending, receiving, decimals):
            with boa.reverts():
                swap.exchange(sending, receiving, 0, 0, sender=charlie)

        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_min_dy_too_high(self, bob, swap, sending, receiving, decimals):
            amount = 10 ** decimals[sending]
            min_dy = swap.get_dy(sending, receiving, amount)
            with boa.reverts():
                swap.exchange(sending, receiving, amount, min_dy + 2, sender=bob)

        @pytest.mark.parametrize("idx", range(2))
        def test_same_coin(self, bob, swap, idx):
            with boa.reverts():
                swap.exchange(idx, idx, 0, 0, sender=bob)

        @pytest.mark.parametrize("idx", [-1, -(2**127)])
        def test_i_below_zero(self, bob, swap, idx):
            with boa.reverts():
                swap.exchange(idx, 0, 0, 0, sender=bob)

        @pytest.mark.parametrize("idx", [9, 2**127 - 1])
        def test_i_above_n_coins(self, bob, swap, idx):
            with boa.reverts():
                swap.exchange(idx, 0, 0, 0, sender=bob)

        @pytest.mark.parametrize("idx", [-1, -(2**127)])
        def test_j_below_zero(self, bob, swap, idx):
            with boa.reverts():
                swap.exchange(0, idx, 0, 0, sender=bob)

        @pytest.mark.parametrize("idx", [9, 2**127 - 1])
        def test_j_above_n_coins(self, bob, swap, idx):
            with boa.reverts():
                swap.exchange(0, idx, 0, 0, sender=bob)

        def test_nonpayable(self, swap, bob):
            with boa.reverts():
                swap.exchange(0, 1, 0, 0, sender=bob, value=1)

    class TestReceiver:
        def test_add_liquidity(self, bob, charlie, swap, deposit_amounts):
            swap.add_liquidity(deposit_amounts, 0, charlie, sender=bob)

            assert swap.balanceOf(bob) == 0
            assert swap.balanceOf(charlie) > 0

        def test_exchange(
            self,
            bob,
            charlie,
            swap,
            pool_type,
            pool_tokens,
            underlying_tokens,
            decimals,
            pool_token_types,
            metapool_token_type,
        ):
            initial_balance = pool_tokens[0].balanceOf(bob) if pool_type == 0 else underlying_tokens[0].balanceOf(bob)

            swap.exchange(1, 0, 1000 * 10**18, 0, charlie, sender=bob)
            if pool_type == 0:
                assert pool_tokens[0].balanceOf(charlie) > 0
                if pool_token_types[0] != 2:
                    assert pool_tokens[0].balanceOf(bob) == initial_balance
                else:
                    assert pool_tokens[0].balanceOf(bob) == pytest.approx(initial_balance, rel=2e-2)
            else:
                assert underlying_tokens[0].balanceOf(charlie) > 0
                if metapool_token_type != 2:
                    assert underlying_tokens[0].balanceOf(bob) == initial_balance
                else:
                    assert underlying_tokens[0].balanceOf(bob) == pytest.approx(initial_balance, rel=2e-2)

        def test_remove_liquidity(
            self,
            bob,
            swap,
            charlie,
            pool_type,
            pool_tokens,
            underlying_tokens,
            initial_amounts,
            pool_size,
            deposit_amounts,
        ):
            swap.add_liquidity(deposit_amounts, 0, sender=bob)
            initial_amount = swap.balanceOf(bob)
            withdraw_amount = initial_amount // 4
            swap.remove_liquidity(withdraw_amount, [0] * pool_size, charlie, sender=bob)

            i = 0
            if pool_type == 0:
                for coin, amount in zip(pool_tokens, deposit_amounts):
                    assert coin.balanceOf(swap) + coin.balanceOf(charlie) == pytest.approx(
                        deposit_amounts[0] * 2, rel=1.5e-2
                    )
                    i += 1
            else:
                for coin, amount in zip(underlying_tokens[:2], deposit_amounts):
                    assert coin.balanceOf(swap) + coin.balanceOf(charlie) == pytest.approx(
                        deposit_amounts[0] * 2, rel=1.5e-2
                    )
                    i += 1

            assert swap.balanceOf(bob) == pytest.approx(deposit_amounts[0] * pool_size - withdraw_amount, rel=1.5e-2)
            assert swap.totalSupply() == pytest.approx(deposit_amounts[0] * 2 * pool_size - withdraw_amount, rel=1.5e-2)

        def test_remove_imbalanced(
            self, bob, swap, charlie, pool_type, pool_tokens, underlying_tokens, initial_amounts, deposit_amounts
        ):
            swap.add_liquidity(deposit_amounts, 0, sender=bob)
            initial_balance = swap.balanceOf(bob)
            amounts = [i // 4 for i in initial_amounts]
            swap.remove_liquidity_imbalance(amounts, initial_balance, charlie, sender=bob)

            if pool_type == 0:
                for i, coin in enumerate(pool_tokens):
                    assert coin.balanceOf(charlie) == pytest.approx(amounts[i], rel=1.5e-2)
                    assert coin.balanceOf(swap) == pytest.approx(initial_amounts[i] - amounts[i], rel=1.5e-2)
            else:
                for i, coin in enumerate(underlying_tokens[:2]):
                    assert coin.balanceOf(charlie) == pytest.approx(amounts[i], rel=1.5e-2)
                    assert coin.balanceOf(swap) == pytest.approx(initial_amounts[i] - amounts[i], rel=1.5e-2)

            assert swap.balanceOf(bob) / initial_balance == pytest.approx(0.5, rel=1.5e-2)

        def test_remove_one_coin(self, alice, charlie, swap, pool_type, pool_tokens, underlying_tokens):
            swap.remove_liquidity_one_coin(10**18, 0, 0, charlie, sender=alice)

            assert swap.balanceOf(charlie) == 0
            assert swap.balanceOf(alice) > 0
