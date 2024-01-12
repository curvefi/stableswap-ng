import boa
import pytest


@pytest.fixture
def empty_factory(deployer, fee_receiver, owner):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/main/CurveStableSwapFactoryNG.vy",
            fee_receiver,
            owner,
        )


def test_add_base_pool(empty_factory, owner, forked_chain):
    fraxusdc = "0xdcef968d416a41cdac0ed8702fac8128a64241a2"
    lp_token = "0x3175df0976dfa876431c2e9ee6bc45b65d3473cc"

    assert empty_factory.base_pool_count() == 0
    empty_factory.add_base_pool(fraxusdc, lp_token, [0, 0], 2, sender=owner)
    assert empty_factory.base_pool_count() == 1
    assert empty_factory.base_pool_list(0).lower() == fraxusdc.lower()
