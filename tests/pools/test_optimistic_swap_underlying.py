import itertools

import boa
import pytest


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.only_for_token_types(0, 1, 2)
@pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
def test_exchange_underlying_received_nonrebasing(
    bob,
    swap,
    transfer_and_swap,
    underlying_tokens,
    mint_bob,
    approve_bob,
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
@pytest.mark.only_for_token_types(0, 1, 2)
@pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
def test_exchange_underlying_not_received(bob, swap, mint_bob, approve_bob, sending, receiving):
    with boa.env.prank(bob), boa.reverts():
        swap.exchange_underlying_received(sending, receiving, 1, 0, False, bob)


@pytest.mark.only_for_pool_type(1)  # only for metapools
@pytest.mark.only_for_token_types(3)
@pytest.mark.parametrize("sending,receiving", list(itertools.combinations([0, 1, 2, 3], 2)))
def test_exchange_underlying_received_rebasing_reverts(
    swap, transfer_and_swap, mint_bob, approve_bob, sending, receiving
):
    with boa.reverts(compiler="external call failed"):
        transfer_and_swap(swap, sending, receiving, True)
