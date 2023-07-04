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
def views_implementation(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/main/CurveStableSwapNGViews.vy")


@pytest.fixture(scope="module")
def factory(
    deployer,
    fee_receiver,
    owner,
    weth,
):
    with boa.env.prank(deployer):
        _factory = boa.load(
            "contracts/main/CurveStableSwapFactoryNG.vy",
            fee_receiver,
            owner,
            weth,
        )
    return _factory


# <---------------------   Functions   --------------------->
@pytest.fixture(scope="module")
def set_plain_implementations(owner, factory, amm_implementation_plain):
    with boa.env.prank(owner):
        factory.set_plain_implementations(0, amm_implementation_plain.address)


@pytest.fixture(scope="module")
def set_meta_implementations(owner, factory, amm_implementation_meta):
    with boa.env.prank(owner):
        factory.set_metapool_implementations(0, amm_implementation_meta.address)


@pytest.fixture(scope="module")
def add_base_pool(
    owner,
    fee_receiver,
    factory,
    base_pool,
    base_pool_lp_token,
    base_pool_tokens,
    zero_address,
):
    with boa.env.prank(owner):
        factory.add_base_pool(
            base_pool.address,
            base_pool_lp_token.address,
            fee_receiver,
            [t.address for t in base_pool_tokens],
            0,
            len(base_pool_tokens),
            [False] * len(base_pool_tokens),
            [zero_address] * len((base_pool_tokens)),
        )


@pytest.fixture(scope="module")
def set_gauge_implementation(owner, factory, gauge_implementation):
    with boa.env.prank(owner):
        factory.set_gauge_implementation(gauge_implementation.address)


@pytest.fixture(scope="module")
def set_views_implementation(owner, factory, views_implementation):
    with boa.env.prank(owner):
        factory.set_views_implementation(views_implementation.address)


@pytest.fixture(scope="module")
def gauge(owner, factory, swap, gauge_interface, set_gauge_implementation):
    with boa.env.prank(owner):
        gauge_address = factory.deploy_gauge(swap.address)
    return gauge_interface.at(gauge_address)
