import boa
import pytest


@pytest.fixture(scope="module")
def weth(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/WETH.vy")


@pytest.fixture(scope="module")
def usdt(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/ERC20.vy", "USDT", "USDT", 6)


@pytest.fixture(scope="module")
def dai(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/ERC20.vy", "DAI", "DAI", 18)


@pytest.fixture(scope="module")
def steth(deployer):
    with boa.env.prank(deployer):
        # TODO: turn this into a rebasing implementation
        return boa.load(
            "contracts/mocks/ERC20Rebasing.vy", "stETH", "stETH", 18
        )


@pytest.fixture(scope="module")
def oracle_token_a(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/mocks/ERC20Oracle.vy",
            "OTA",
            "OTA",
            18,
            1006470359024000000,
        )


@pytest.fixture(scope="module")
def oracle_token_b(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/mocks/ERC20Oracle.vy",
            "OTB",
            "OTB",
            8,
            1007580460035000000,
        )


@pytest.fixture(scope="module")
def plain_coins(usdt, dai):
    yield [usdt, dai]


@pytest.fixture(scope="module")
def rebasing_coins(weth, steth):
    yield [steth, weth]
