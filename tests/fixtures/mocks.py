import boa
import pytest


@pytest.fixture(scope="function")
def callback_contract(bob, swap, pool_tokens, underlying_tokens):

    with boa.env.prank(bob):
        _callback = boa.load("contracts/mocks/CallbackSwap.vy", swap.address, bob)
        for token in pool_tokens + underlying_tokens:
            token.approve(_callback.address, 2**256 - 1)

    return _callback
