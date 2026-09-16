import inspect

import boa
import pytest


# implementations are immutable, so deploy once per module rather than per test;
# not per session, because boa_setup swaps in a fresh boa.Env for every module
@pytest.fixture(scope="module")
def gauge_implementation(deployer, gauge_deployer):
    with boa.env.prank(deployer):
        return gauge_deployer.deploy_as_blueprint()


@pytest.fixture(scope="module")
def amm_implementation(deployer, amm_deployer):
    with boa.env.prank(deployer):
        return amm_deployer.deploy_as_blueprint()


@pytest.fixture(scope="module")
def amm_implementation_meta(deployer, meta_deployer):
    with boa.env.prank(deployer):
        return meta_deployer.deploy_as_blueprint()


@pytest.fixture(scope="module")
def views_implementation(deployer, views_deployer):
    with boa.env.prank(deployer):
        return views_deployer.deploy()


@pytest.fixture(scope="module")
def math_implementation(deployer, math_deployer):
    with boa.env.prank(deployer):
        return math_deployer.deploy()


@pytest.fixture()
def factory(
    deployer, fee_receiver, owner, gauge_implementation, views_implementation, math_implementation, factory_deployer
):
    with boa.env.prank(deployer):
        factory = factory_deployer.deploy(fee_receiver, owner)

    with boa.env.prank(owner):
        factory.set_gauge_implementation(gauge_implementation.address)
        factory.set_views_implementation(views_implementation.address)
        factory.set_math_implementation(math_implementation.address)

    return factory


# titanoboa anchors fixtures and unwinds them in reverse: an implementation first created inside a test
# would sit above that test's function fixtures, and their block/timestamp changes would never be unwound.
# Forking modules skip this, since a fork replaces the state under anchors already taken.
@pytest.fixture(scope="module", autouse=True)
def implementations_before_any_test(request, boa_setup):
    items = [item for item in request.session.items if item.module is request.module]
    if any("forked_chain" in item.fixturenames for item in items) or "env.fork(" in inspect.getsource(request.module):
        return
    for name in (
        "gauge_implementation",
        "amm_implementation",
        "amm_implementation_meta",
        "views_implementation",
        "math_implementation",
    ):
        request.getfixturevalue(name)


# <---------------------   Functions   --------------------->
@pytest.fixture()
def set_pool_implementations(owner, factory, amm_implementation):
    with boa.env.prank(owner):
        factory.set_pool_implementations(0, amm_implementation.address)


@pytest.fixture()
def set_metapool_implementations(owner, factory, amm_implementation_meta):
    with boa.env.prank(owner):
        factory.set_metapool_implementations(0, amm_implementation_meta.address)


@pytest.fixture()
def add_base_pool(owner, factory, base_pool, base_pool_lp_token, base_pool_tokens):
    with boa.env.prank(owner):
        factory.add_base_pool(
            base_pool.address, base_pool_lp_token.address, [0] * len(base_pool_tokens), len(base_pool_tokens)
        )


@pytest.fixture()
def set_gauge_implementation(owner, factory, gauge_implementation):
    with boa.env.prank(owner):
        factory.set_gauge_implementation(gauge_implementation.address)


@pytest.fixture()
def set_views_implementation(owner, factory, views_implementation):
    with boa.env.prank(owner):
        factory.set_views_implementation(views_implementation.address)


@pytest.fixture()
def set_math_implementation(owner, factory, math_implementation):
    with boa.env.prank(owner):
        factory.set_math_implementation(math_implementation.address)


@pytest.fixture()
def gauge(owner, factory, swap, gauge_deployer, set_gauge_implementation):
    with boa.env.prank(owner):
        gauge_address = factory.deploy_gauge(swap.address)
    return gauge_deployer.at(gauge_address)
