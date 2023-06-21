import boa
import pytest


@pytest.fixture(scope="module")
def weth(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/WETH.vy")


@pytest.fixture(scope="module")
def usdt(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/ERC20Mock.vy", "USDT", "USDT", 6)


@pytest.fixture(scope="module")
def dai(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/ERC20Mock.vy", "DAI", "DAI", 18)


@pytest.fixture(scope="module")
def steth(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/ERC20Mock.vy", "stETH", "stETH", 18)


@pytest.fixture(scope="module")
def plain_coins(usdt, dai):
    yield [usdt, dai]


@pytest.fixture(scope="module")
def rebasing_coins(weth, steth):
    yield [steth, weth]
