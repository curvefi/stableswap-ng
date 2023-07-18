import boa
import pytest

SWAP_AMOUNT = 500_000


class TestOptimisticSwap:
    @pytest.fixture(scope="module")
    def callback_contract(self, bob, swap, mint_bob, pool_tokens):

        with boa.env.prank(bob):
            _callback = boa.load("contracts/mocks/CallbackSwap.vy", swap.address, bob)
            for token in pool_tokens:
                token.approve(_callback.address, 2**256 - 1)

        return _callback

    @pytest.fixture(scope="module")
    def transfer_and_swap(self, callback_contract, bob):
        def _transfer_and_swap(swap, pool_tokens, sending, receiving, underlying):

            coin = pool_tokens[sending]
            amount_in = SWAP_AMOUNT * 10 ** (coin.decimals())

            assert coin.address == swap.coins(sending)

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

            return {
                "amount_in": amount_in,
                "amount_out": amount_out,
                "bob": {
                    "sending_token": [bob_sending_balance_before, bob_sending_balance_after],
                    "receiving_token": [bob_receiving_balance_before, bob_receiving_balance_after],
                },
                "swap": {
                    "sending_token": [pool_sending_balance_before, pool_sending_balance_after],
                    "receiving_token": [pool_receiving_balance_before, pool_receiving_balance_after],
                },
            }

        return _transfer_and_swap

    @pytest.mark.usefixtures("add_initial_liquidity_alice", "mint_bob", "approve_bob")
    class TestExchangeReceived:

        # TODO: need to permutate/combinate N_COIN combos.
        @pytest.mark.only_for_token_types(0, 1, 2)
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_exchange_received_nonrebasing(self, bob, swap, transfer_and_swap, pool_tokens, sending, receiving):

            swap_data = transfer_and_swap(swap, pool_tokens, sending, receiving, False)

            assert swap_data["bob"]["sending_token"][0] - swap_data["bob"]["sending_token"][1] == swap_data["amount_in"]
            assert (
                swap_data["bob"]["receiving_token"][1] - swap_data["bob"]["receiving_token"][0]
                == swap_data["amount_out"]
            )

            assert (
                swap_data["swap"]["sending_token"][1] - swap_data["swap"]["sending_token"][0] == swap_data["amount_in"]
            )
            assert (
                swap_data["swap"]["receiving_token"][0] - swap_data["swap"]["receiving_token"][1]
                == swap_data["amount_out"]
            )

        @pytest.mark.only_for_token_types(0, 1, 2)
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_exchange_not_received(self, bob, swap, pool_tokens, sending, receiving):

            coin = pool_tokens[sending]
            amount_in = SWAP_AMOUNT * 10 ** (coin.decimals())
            assert coin.address == swap.coins(sending)

            with boa.env.prank(bob), boa.reverts("Pool did not receive tokens for swap"):
                swap.exchange_received(sending, receiving, amount_in, 0, False, bob)

        @pytest.mark.only_for_token_types(3)
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_exchange_received_rebasing(self, bob, swap, transfer_and_swap, pool_tokens, sending, receiving):

            with boa.env.prank(bob), boa.reverts(compiler="external call failed"):
                transfer_and_swap(swap, pool_tokens, sending, receiving, False)

    @pytest.mark.only_for_pool_type(1)  # only for metapools
    @pytest.mark.usefixtures("add_initial_liquidity_alice", "mint_bob", "approve_bob")
    class TestExchangeUnderlyingReceived:
        pass
