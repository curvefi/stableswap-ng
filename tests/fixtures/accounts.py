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
def mint_account(account, underlying_tokens, initial_balance, initial_amounts, pool_type):
    mint_for_testing(account, initial_balance, None, True)

    pool_tokens = underlying_tokens.copy()
    if pool_type == 1:
        pool_tokens.pop(1)

    for pool_token, amount in zip(pool_tokens, initial_amounts):
        mint_for_testing(account, amount, pool_token, False)


def approve_account(account, tokens, swap):
    for token in tokens:
        with boa.env.prank(account):
            token.approve(swap.address, 2**256 - 1)


@pytest.fixture(scope="module")
def mint_owner(owner, pool_tokens, initial_balance, initial_amounts, pool_type):
    mint_account(owner, pool_tokens, initial_balance, initial_amounts, pool_type)


@pytest.fixture(scope="module")
def approve_owner(owner, pool_tokens, empty_swap):
    approve_account(owner, pool_tokens, empty_swap)


@pytest.fixture(scope="module")
def mint_alice(alice, underlying_tokens, initial_balance, initial_amounts, pool_type):
    mint_account(alice, underlying_tokens, initial_balance, initial_amounts, pool_type)


@pytest.fixture(scope="module")
def approve_alice(alice, underlying_tokens, empty_swap):
    approve_account(alice, underlying_tokens, empty_swap)


@pytest.fixture(scope="module")
def mint_bob(bob, underlying_tokens, initial_balance, initial_amounts, pool_type):
    mint_account(bob, underlying_tokens, initial_balance, initial_amounts, pool_type)


@pytest.fixture(scope="module")
def approve_bob(bob, underlying_tokens, empty_swap):
    approve_account(bob, underlying_tokens, empty_swap)
