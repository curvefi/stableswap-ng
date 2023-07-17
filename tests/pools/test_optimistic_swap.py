import boa
import pytest

# from tests.utils.transactions import call_returning_result_and_logs

SWAP_AMOUNT = 500_000


class TestOptimisticSwap:
    @pytest.fixture(scope="module")
    def callback_contract(self, bob, swap, mint_bob, pool_tokens):

        with boa.env.prank(bob):
            _callback = boa.load("contracts/mocks/CallbackSwap.vy", swap.address, bob)
            for token in pool_tokens:
                token.approve(_callback.address, 2**256 - 1)

        return _callback

    @pytest.mark.usefixtures("add_initial_liquidity_alice", "mint_bob", "approve_bob")
    class TestExchangeReceived:

        # TODO: need to permutate/combinate N_COIN combos.
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_exchange_received(self, bob, swap, callback_contract, pool_tokens, sending, receiving, zero_address):

            coin = pool_tokens[sending]
            assert coin.address == swap.coins(sending)
            amount_in = SWAP_AMOUNT * 10 ** (coin.decimals())
            underlying = False

            bob_sending_balance_before = pool_tokens[sending].balanceOf(bob)
            bob_receiving_balance_before = pool_tokens[receiving].balanceOf(bob)
            pool_sending_balance_before = pool_tokens[sending].balanceOf(swap.address)
            pool_receiving_balance_before = pool_tokens[receiving].balanceOf(swap.address)

            with boa.env.prank(bob):
                amount_out = callback_contract.transfer_and_swap(sending, receiving, amount_in, 0, underlying)
                assert amount_out > 0

            bob_sending_balance_after = pool_tokens[sending].balanceOf(bob)
            bob_receiving_balance_after = pool_tokens[receiving].balanceOf(bob)
            pool_sending_balance_after = pool_tokens[sending].balanceOf(swap.address)
            pool_receiving_balance_after = pool_tokens[receiving].balanceOf(swap.address)

            # TODO: incorporate cases for different asset types:
            assert bob_sending_balance_before - bob_sending_balance_after == amount_in
            assert bob_receiving_balance_after - bob_receiving_balance_before == amount_out

            assert pool_sending_balance_after - pool_sending_balance_before == amount_in
            assert pool_receiving_balance_before - pool_receiving_balance_after == amount_out

    # TODO: Add tests for exchange_underlying_received
    # @pytest.mark.usefixtures("add_initial_liquidity_alice", "mint_bob", "approve_bob")
    # class TestExchangeUnderlyingReceived:
    #     pass
