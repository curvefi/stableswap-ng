import boa
import pytest


@pytest.fixture(scope="module")
def gauge_interface():
    return boa.load_partial("contracts/main/LiquidityGauge.vy")


@pytest.fixture(scope="module")
def gauge_implementation(deployer, gauge_interface):
    with boa.env.prank(deployer):
        return gauge_interface.deploy_as_blueprint()


@pytest.fixture(scope="module")
def amm_interface_plain():
    return boa.load_partial("contracts/main/CurveStableSwap2NG.vy")


@pytest.fixture(scope="module")
def amm_implementation_plain(deployer, amm_interface_plain):
    with boa.env.prank(deployer):
        return amm_interface_plain.deploy_as_blueprint()


@pytest.fixture(scope="module")
def amm_interface_meta():
    return boa.load_partial("contracts/main/CurveStableSwapMetaNG.vy")


@pytest.fixture(scope="module")
def amm_implementation_meta(deployer, amm_interface_meta):
    with boa.env.prank(deployer):
        return amm_interface_meta.deploy_as_blueprint()


@pytest.fixture(scope="module")
def factory(
    deployer,
    fee_receiver,
    owner,
    amm_implementation_plain,
    gauge_implementation,
    weth,
):
    with boa.env.prank(deployer):
        _factory = boa.load(
            "contracts/main/CurveStableSwapFactoryNG.vy",
            fee_receiver,
            owner,
            weth,
        )

    with boa.env.prank(owner):
        _factory.set_plain_implementations(2, 0, amm_implementation_plain)
        _factory.set_gauge_implementation(gauge_implementation)
        # TODO: add Factory Meta Implementation

    return _factory


@pytest.fixture(scope="module")
def factory_populated(
    factory, swap_plain, swap_eth_rebasing, swap_oracle, swap_meta
):
    return factory
