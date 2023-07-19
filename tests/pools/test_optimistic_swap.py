import boa
import pytest


# TODO: need to permutate/combinate N_COIN combos.
@pytest.mark.only_for_token_types(0, 1, 2)
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange_received_nonrebasing(
    bob, swap, transfer_and_swap, pool_tokens, mint_bob, approve_bob, sending, receiving
):

    swap_data = transfer_and_swap(swap, sending, receiving, False)

    assert swap_data["bob"]["sending_token"][0] - swap_data["bob"]["sending_token"][1] == swap_data["amount_in"]
    assert swap_data["bob"]["receiving_token"][1] - swap_data["bob"]["receiving_token"][0] == swap_data["amount_out"]

    assert swap_data["swap"]["sending_token"][1] - swap_data["swap"]["sending_token"][0] == swap_data["amount_in"]
    assert swap_data["swap"]["receiving_token"][0] - swap_data["swap"]["receiving_token"][1] == swap_data["amount_out"]


@pytest.mark.only_for_token_types(0, 1, 2)
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange_not_received(bob, swap, pool_tokens, mint_bob, approve_bob, sending, receiving):
    with boa.env.prank(bob), boa.reverts("Pool did not receive tokens for swap"):
        swap.exchange_received(sending, receiving, 1, 0, False, bob)


@pytest.mark.only_for_token_types(3)
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_exchange_received_rebasing_reverts(
    bob, swap, transfer_and_swap, pool_tokens, mint_bob, approve_bob, sending, receiving
):

    with boa.reverts(compiler="external call failed"):
        transfer_and_swap(swap, sending, receiving, False)
