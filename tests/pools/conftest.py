import boa
import pytest

SWAP_AMOUNT = 50


@pytest.fixture(scope="module")
def transfer_and_swap(
    callback_contract,
    bob,
    underlying_tokens,
    pool_type,
    base_pool,
):
    def _transfer_and_swap(pool, sending, receiving, underlying):

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
        pool_sending_balance_before = input_coin.balanceOf(pool.address)
        pool_receiving_balance_before = output_coin.balanceOf(pool.address)
        base_pool_sending_balance_before = input_coin.balanceOf(base_pool.address)
        base_pool_receiving_balance_before = output_coin.balanceOf(base_pool.address)

        with boa.env.prank(bob):
            amount_out = callback_contract.transfer_and_swap(sending, receiving, amount_in, 0, underlying)
            assert amount_out > 0

        bob_sending_balance_after = input_coin.balanceOf(bob)
        bob_receiving_balance_after = output_coin.balanceOf(bob)
        pool_sending_balance_after = input_coin.balanceOf(pool.address)
        pool_receiving_balance_after = output_coin.balanceOf(pool.address)
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
