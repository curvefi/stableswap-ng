import boa
import pytest


@pytest.fixture()
def callback_contract(bob, swap, pool_tokens, underlying_tokens, callback_swap_deployer):
    with boa.env.prank(bob):
        callback = callback_swap_deployer.deploy(swap.address, bob)
        for token in pool_tokens + underlying_tokens:
            token.approve(callback.address, 2**256 - 1)

    return callback
