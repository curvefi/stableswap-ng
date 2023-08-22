import boa
import pytest


class TestFactoryForked:
    @pytest.fixture
    def empty_factory(self, deployer, fee_receiver, owner):
        with boa.env.prank(deployer):
            _factory = boa.load(
                "contracts/main/CurveStableSwapFactoryNG.vy",
                fee_receiver,
                owner,
            )
        return _factory

    @pytest.mark.only_for_pool_type(1)
    def test_add_base_pool(self, empty_factory, owner, forked_chain):
        susd_pool = "0xA5407eAE9Ba41422680e2e00537571bcC53efBfD"
        lp_token = "0xC25a3A3b969415c80451098fa907EC722572917F"
        coins = [
            "0x6B175474E89094C44Da98b954EedeAC495271d0F",
            "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
            "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            "0x57Ab1ec28D129707052df4dF418D58a2D46d5f51",
        ]

        assert empty_factory.base_pool_count() == 0
        empty_factory.add_base_pool(susd_pool, lp_token, coins, [0] * len(coins), len(coins), sender=owner)
        assert empty_factory.base_pool_count() == 1
        assert empty_factory.base_pool_list(0) == susd_pool
