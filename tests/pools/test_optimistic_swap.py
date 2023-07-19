import itertools

import boa
import pytest

SWAP_AMOUNT = 50


class TestOptimisticSwap:
    @pytest.fixture(scope="module")
    def callback_contract(self, bob, swap, mint_bob, underlying_tokens):

        with boa.env.prank(bob):
            _callback = boa.load("contracts/mocks/CallbackSwap.vy", swap.address, bob)
            for token in underlying_tokens:
                token.approve(_callback.address, 2**256 - 1)

        return _callback

    @pytest.fixture(scope="module")
    def transfer_and_swap(
        self,
        callback_contract,
        bob,
        underlying_tokens,
        pool_type,
        base_pool,
    ):
        def _transfer_and_swap(swap, sending, receiving, underlying):

            sending_token = "swap"
            receiving_token = "swap"

            if pool_type == 1:

                if sending == 0:
                    input_coin = underlying_tokens[0]
                else:
                    base_i = sending - 1
                    input_coin = underlying_tokens[2 + base_i]
                    sending_token = "base_pool"
                if receiving == 0:
                    output_coin = underlying_tokens[0]
                else:
                    base_j = receiving - 1
                    output_coin = underlying_tokens[2 + base_j]
                    receiving_token = "base_pool"

            else:

                input_coin = underlying_tokens[sending]
                output_coin = underlying_tokens[receiving]

            amount_in = SWAP_AMOUNT * 10 ** (input_coin.decimals())

            bob_sending_balance_before = input_coin.balanceOf(bob)
            assert bob_sending_balance_before >= amount_in

            bob_receiving_balance_before = output_coin.balanceOf(bob)
            pool_sending_balance_before = input_coin.balanceOf(swap.address)
            pool_receiving_balance_before = output_coin.balanceOf(swap.address)
            base_pool_sending_balance_before = input_coin.balanceOf(base_pool.address)
            base_pool_receiving_balance_before = output_coin.balanceOf(base_pool.address)

            with boa.env.prank(bob):
                amount_out = callback_contract.transfer_and_swap(sending, receiving, amount_in, 0, underlying)
                assert amount_out > 0

            bob_sending_balance_after = input_coin.balanceOf(bob)
            bob_receiving_balance_after = output_coin.balanceOf(bob)
            pool_sending_balance_after = input_coin.balanceOf(swap.address)
            pool_receiving_balance_after = output_coin.balanceOf(swap.address)
            base_pool_sending_balance_after = input_coin.balanceOf(base_pool.address)
            base_pool_receiving_balance_after = output_coin.balanceOf(base_pool.address)

            return {
                "amount_in": amount_in,
                "amount_out": amount_out,
                "sending_token_pool": sending_token,
                "receiving_token_pool": receiving_token,
                "bob": {
                    "sending_token": [bob_sending_balance_before, bob_sending_balance_after],
                    "receiving_token": [bob_receiving_balance_before, bob_receiving_balance_after],
                },
                "swap": {
                    "sending_token": [pool_sending_balance_before, pool_sending_balance_after],
                    "receiving_token": [pool_receiving_balance_before, pool_receiving_balance_after],
                },
                "base_pool": {
                    "sending_token": [base_pool_sending_balance_before, base_pool_sending_balance_after],
                    "receiving_token": [base_pool_receiving_balance_before, base_pool_receiving_balance_after],
                },
            }

        return _transfer_and_swap

    @pytest.mark.usefixtures("add_initial_liquidity_alice", "mint_bob", "approve_bob")
    class TestExchangeReceived:

        # TODO: need to permutate/combinate N_COIN combos.
        @pytest.mark.only_for_token_types(0, 1, 2)
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_exchange_received_nonrebasing(self, bob, swap, transfer_and_swap, pool_tokens, sending, receiving):

            swap_data = transfer_and_swap(swap, sending, receiving, False)

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
        def test_exchange_received_rebasing_reverts(
            self, bob, swap, transfer_and_swap, pool_tokens, sending, receiving
        ):

            with boa.env.prank(bob), boa.reverts(compiler="external call failed"):
                transfer_and_swap(swap, sending, receiving, False)

    @pytest.mark.only_for_pool_type(1)  # only for metapools
    @pytest.mark.usefixtures("add_initial_liquidity_metapool_alice", "mint_bob", "approve_bob")
    class TestExchangeUnderlyingReceived:
        @pytest.mark.only_for_token_types(0, 1, 2)
        @pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
        def test_exchange_underlying_received_nonrebasing(
            self, bob, swap, transfer_and_swap, underlying_tokens, sending, receiving
        ):

            swap_data = transfer_and_swap(swap, sending, receiving, True)

            assert swap_data["bob"]["sending_token"][0] - swap_data["bob"]["sending_token"][1] == swap_data["amount_in"]
            assert (
                swap_data["bob"]["receiving_token"][1] - swap_data["bob"]["receiving_token"][0]
                == swap_data["amount_out"]
            )

            # sending token swap balances should go up for sending_token_pool
            # (could be base pool could be metapool):
            sending_token_pool = swap_data["sending_token_pool"]
            receiving_token_pool = swap_data["receiving_token_pool"]
            assert (
                swap_data[sending_token_pool]["sending_token"][1] - swap_data[sending_token_pool]["sending_token"][0]
                == swap_data["amount_in"]
            )

            # receiving token swap balances should go down for receiving_token_pool
            # (could be base pool could be metapool):
            assert (
                swap_data[receiving_token_pool]["receiving_token"][0]
                - swap_data[receiving_token_pool]["receiving_token"][1]
                == swap_data["amount_out"]
            )
