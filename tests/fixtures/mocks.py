import boa
import pytest


@pytest.fixture(scope="module")
def callback_contract(bob, empty_swap, mint_bob, underlying_tokens):

    with boa.env.prank(bob):
        _callback = boa.load("contracts/mocks/CallbackSwap.vy", empty_swap.address, bob)
        for token in underlying_tokens:
            token.approve(_callback.address, 2**256 - 1)

    return _callback
