import boa
import pytest
from boa.environment import AddressType
from eth_account.account import Account, LocalAccount

from tests.utils.tokens import mint_for_testing


@pytest.fixture(scope="module")
def deployer() -> AddressType:
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def owner() -> AddressType:
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def fee_receiver() -> AddressType:
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def eth_acc() -> LocalAccount:
    return Account.create()


@pytest.fixture(scope="module")
def alice():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def bob():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def charlie():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def dave():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def erin():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def frank():
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def accounts(bob, charlie, dave, erin, frank):
    return [bob, charlie, dave, erin, frank]


# <---------------------   Functions   --------------------->
def mint_account(account, pool_tokens, initial_amounts):
    mint_for_testing(account, 10**18, None, True)
    for pool_token, amount in zip(pool_tokens, initial_amounts):
        mint_for_testing(account, amount, pool_token, False)


def approve_account(account, pool_tokens, swap):
    for pool_token in pool_tokens:
        with boa.env.prank(account):
            pool_token.approve(swap.address, 2**256 - 1)


@pytest.fixture(scope="module")
def mint_owner(owner, pool_tokens, initial_amounts):
    mint_account(owner, pool_tokens, initial_amounts)


@pytest.fixture(scope="module")
def approve_owner(owner, pool_tokens, swap):
    approve_account(owner, pool_tokens, swap)


@pytest.fixture(scope="module")
def mint_alice(alice, pool_tokens, initial_amounts):
    mint_account(alice, pool_tokens, initial_amounts)


@pytest.fixture(scope="module")
def approve_alice(alice, pool_tokens, swap):
    approve_account(alice, pool_tokens, swap)


@pytest.fixture(scope="module")
def mint_bob(bob, pool_tokens, initial_amounts):
    mint_account(bob, pool_tokens, initial_amounts)


@pytest.fixture(scope="module")
def approve_bob(bob, pool_tokens, swap):
    approve_account(bob, pool_tokens, swap)
