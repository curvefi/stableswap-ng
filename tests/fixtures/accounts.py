import boa
import pytest
from boa.environment import AddressType
from eth_account.account import Account, LocalAccount


@pytest.fixture(scope="module")
def deployer() -> AddressType:
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def owner() -> AddressType:
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def factory_admin(factory) -> AddressType:
    return factory.admin()


@pytest.fixture(scope="module")
def fee_receiver() -> AddressType:
    return boa.env.generate_address()


@pytest.fixture(scope="module")
def eth_acc() -> LocalAccount:
    return Account.create()
