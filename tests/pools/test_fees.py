import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


class TestFees:
    @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
    def test_admin_balances(
        self, bob, swap, pool_type, pool_tokens, underlying_tokens, initial_amounts, sending, receiving
    ):
        for send, recv in [(sending, receiving), (receiving, sending)]:
            swap.exchange(
                send,
                recv,
                initial_amounts[send],
                0,
                sender=bob,
            )

        for i in (sending, receiving):
            if pool_type == 0:
                admin_fee = pool_tokens[i].balanceOf(swap) - swap.balances(i)
                assert admin_fee > 0
            else:
                admin_fee = underlying_tokens[i].balanceOf(swap) - swap.balances(i)
                assert admin_fee > 0

    @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
    def test_withdraw_one_coin(
        self,
        alice,
        bob,
        fee_receiver,
        swap,
        pool_type,
        pool_tokens,
        underlying_tokens,
        sending,
        receiving,
        initial_amounts,
    ):
        swap.exchange(
            sending,
            receiving,
            initial_amounts[sending],
            0,
            sender=bob,
        )

        admin_balance = swap.admin_balances(receiving)

        assert admin_balance > 0
        assert swap.admin_balances(sending) == 0

        swap.withdraw_admin_fees(sender=alice)
        swap_balance = (
            pool_tokens[receiving].balanceOf(swap) if pool_type == 0 else underlying_tokens[receiving].balanceOf(swap)
        )
        assert swap.balances(receiving) == swap_balance
        assert (
            admin_balance == pool_tokens[receiving].balanceOf(fee_receiver)
            if pool_type == 0
            else underlying_tokens[receiving].balanceOf(fee_receiver)
        )

    def test_no_fees(self, bob, fee_receiver, swap, pool_type, pool_tokens, underlying_tokens):
        swap.withdraw_admin_fees(sender=bob)

        if pool_type == 0:
            for coin in pool_tokens:
                assert coin.balanceOf(fee_receiver) == 0
        else:
            for coin in underlying_tokens:
                assert coin.balanceOf(fee_receiver) == 0

    def test_withdraw_admin_fees(self, bob, swap, pool_type, pool_tokens, underlying_tokens, fee_receiver):
        swap.exchange(1, 0, 10**18, 0, sender=bob)

        fees = []
        if pool_type == 0:
            for i, coin in enumerate(pool_tokens):
                assert coin.balanceOf(fee_receiver) == 0
                fees.append(swap.admin_balances(i))
        else:
            for i, coin in enumerate(underlying_tokens[:2]):
                assert coin.balanceOf(fee_receiver) == 0
                fees.append(swap.admin_balances(i))

        swap.withdraw_admin_fees({"from": bob})
        if pool_type == 0:
            for i, coin in enumerate(pool_tokens):
                assert coin.balanceOf(fee_receiver) == fees[i]
        else:
            for i, coin in enumerate(underlying_tokens[:2]):
                assert coin.balanceOf(fee_receiver) == fees[i]
