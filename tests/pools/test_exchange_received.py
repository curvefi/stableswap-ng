import itertools

import boa
import pytest

from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils.tokens import mint_for_testing

SWAP_AMOUNT = INITIAL_AMOUNT // 1000
pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.fixture(scope="function")
def transfer_and_swap(
    callback_contract,
    bob,
    pool_tokens,
    underlying_tokens,
    pool_type,
    base_pool,
    base_pool_lp_token,
    base_pool_tokens,
    base_pool_decimals,
):
    def _transfer_and_swap(pool, sending: int, receiving: int, underlying: bool):

        # get input and output tokens:
        sending_token = "swap"
        receiving_token = "swap"

        if pool_type == 1:

            if underlying:

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

        else:

            input_coin = pool_tokens[sending]
            output_coin = pool_tokens[receiving]

        # calc amount in:
        amount_in = SWAP_AMOUNT * 10 ** (input_coin.decimals())

        if amount_in > input_coin.balanceOf(bob):
            mint_for_testing(bob, amount_in, input_coin, False)

        # record balances before
        bob_sending_balance_before = input_coin.balanceOf(bob)  # always INITIAL_AMOUNT
        bob_receiving_balance_before = output_coin.balanceOf(bob)  # always INITIAL_AMOUNT
        pool_sending_balance_before = input_coin.balanceOf(pool.address)
        pool_receiving_balance_before = output_coin.balanceOf(pool.address)
        base_pool_sending_balance_before = input_coin.balanceOf(base_pool.address)
        base_pool_receiving_balance_before = output_coin.balanceOf(base_pool.address)

        # swap
        with boa.env.prank(bob):
            amount_out = callback_contract.transfer_and_swap(sending, receiving, input_coin, amount_in, 0, underlying)
            assert amount_out > 0

        # record balances after
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


# TODO: need to permutate/combinate N_COIN combos.
@pytest.mark.only_for_token_types(0, 1)
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange_received_nonrebasing(
    bob,
    swap,
    pool_tokens,
    sending,
    receiving,
    transfer_and_swap,
):
    swap_data = transfer_and_swap(swap, sending, receiving, False)

    assert swap_data["bob"]["sending_token"][0] - swap_data["bob"]["sending_token"][1] == swap_data["amount_in"]
    assert swap_data["bob"]["receiving_token"][1] - swap_data["bob"]["receiving_token"][0] == swap_data["amount_out"]

    assert swap_data["swap"]["sending_token"][1] - swap_data["swap"]["sending_token"][0] == swap_data["amount_in"]
    assert swap_data["swap"]["receiving_token"][0] - swap_data["swap"]["receiving_token"][1] == swap_data["amount_out"]


@pytest.mark.only_for_token_types(0, 1)
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange_not_received(bob, swap, pool_tokens, sending, receiving):
    with boa.env.prank(bob), boa.reverts():
        swap.exchange_received(sending, receiving, 1, 0, bob)


@pytest.mark.only_for_token_types(2)
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange_received_rebasing_reverts(bob, swap, transfer_and_swap, pool_tokens, sending, receiving):
    with boa.reverts():
        transfer_and_swap(swap, sending, receiving, False)


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.only_for_token_types(0, 1)
@pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
def test_exchange_underlying_received_nonrebasing(
    bob,
    swap,
    transfer_and_swap,
    underlying_tokens,
    sending,
    receiving,
):
    swap_data = transfer_and_swap(swap, sending, receiving, True)

    assert swap_data["bob"]["sending_token"][0] - swap_data["bob"]["sending_token"][1] == swap_data["amount_in"]
    assert swap_data["bob"]["receiving_token"][1] - swap_data["bob"]["receiving_token"][0] == swap_data["amount_out"]

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
        swap_data[receiving_token_pool]["receiving_token"][0] - swap_data[receiving_token_pool]["receiving_token"][1]
        == swap_data["amount_out"]
    )


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.only_for_token_types(0, 1)
@pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
def test_exchange_underlying_not_received(bob, swap, sending, receiving):
    with boa.env.prank(bob), boa.reverts():
        swap.exchange_underlying_received(sending, receiving, 1, 0, bob)


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.only_for_token_types(2)
@pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
def test_exchange_underlying_received_rebasing_reverts(swap, transfer_and_swap, sending, receiving):
    if sending == 0:
        with boa.reverts():
            transfer_and_swap(swap, sending, receiving, True)
