import boa
import pytest


@pytest.fixture(scope="session")
def base_pool_deployer():
    return boa.load_partial("contracts/mocks/CurvePool.vy")


@pytest.fixture(scope="session")
def erc20_deployer():
    return boa.load_partial("contracts/mocks/ERC20.vy")


@pytest.fixture(scope="session")
def erc20_rebasing_deployer():
    return boa.load_partial("contracts/mocks/ERC20Rebasing.vy")


@pytest.fixture(scope="session")
def erc4626_deployer():
    return boa.load_partial("contracts/mocks/ERC4626.vy")


@pytest.fixture(scope="session")
def erc20oracle_deployer():
    return boa.load_partial("contracts/mocks/ERC20Oracle.vy")


@pytest.fixture(scope="session")
def erc20rebasing_conditional_deployer():
    return boa.load_partial("contracts/mocks/ERC20RebasingConditional.vy")


@pytest.fixture(scope="session")
def curve_token_v3_deployer():
    return boa.load_partial("contracts/mocks/CurveTokenV3.vy")


@pytest.fixture(scope="session")
def zap_deployer():
    return boa.load_partial("contracts/mocks/Zap.vy")


@pytest.fixture(scope="session")
def gauge_deployer():
    return boa.load_partial("contracts/main/LiquidityGauge.vy")


@pytest.fixture(scope="session")
def amm_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapNG.vy")


@pytest.fixture(scope="session")
def meta_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapMetaNG.vy")


@pytest.fixture(scope="session")
def factory_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapFactoryNG.vy")


@pytest.fixture(scope="session")
def views_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapNGViews.vy")


@pytest.fixture(scope="session")
def math_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapNGMath.vy")


@pytest.fixture(scope="session")
def callback_swap_deployer():
    return boa.load_partial("contracts/mocks/CallbackSwap.vy")
