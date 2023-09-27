import itertools

import boa
import pytest

MAX_COINS = 8


class TestFactory:
    class TestGeneral:
        def test_get_A(self, factory, swap):
            assert factory.get_A(swap.address) == swap.A()

        def test_get_fees(self, factory, swap):
            assert factory.get_fees(swap.address) == (swap.fee(), swap.admin_fee())

        def test_get_admin_balances(self, factory, swap, pool_size):
            balances = [swap.admin_balances(i) for i in range(pool_size)]
            assert factory.get_admin_balances(swap.address) == balances

        def test_fee_receiver(self, factory, fee_receiver):
            assert factory.fee_receiver() == fee_receiver

    @pytest.mark.only_for_pool_type(0)
    class TestBasic:
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_find_pool_for_coins(self, factory, swap, pool_tokens, sending, receiving):
            assert (
                factory.find_pool_for_coins(pool_tokens[sending].address, pool_tokens[receiving].address)
                == swap.address
            )

        def test_get_n_coins(self, factory, swap, pool_tokens, pool_size):
            assert factory.get_n_coins(swap.address) == 2

        def test_get_coins(self, factory, swap, pool_tokens, pool_size):
            assert factory.get_coins(swap.address) == [pt.address for pt in pool_tokens]

        def test_get_decimals(self, factory, swap, decimals):
            assert factory.get_decimals(swap.address) == decimals

        def test_get_balances(self, factory, swap, pool_size):
            assert factory.get_balances(swap.address) == [swap.balances(i) for i in range(pool_size)]

        @pytest.mark.only_for_pool_type(0)
        def test_get_underlying_balances(self, factory, swap):
            with boa.reverts() as e:
                factory.get_underlying_balances(swap.address)
                assert str(e) == "dev: pool is not a metapool"

        def test_get_A(self, factory, swap):
            assert factory.get_A(swap.address) == swap.A()

        def test_get_fees(self, factory, swap):
            assert factory.get_fees(swap.address) == (swap.fee(), swap.admin_fee())

        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_get_coin_indices(self, factory, swap, sending, receiving, pool_tokens):
            i, j, is_underlying = factory.get_coin_indices(
                swap.address, pool_tokens[sending].address, pool_tokens[receiving].address
            )
            assert i == sending
            assert j == receiving

        def test_get_implementation_address(self, factory, swap, amm_implementation):
            assert factory.get_implementation_address(swap.address) == amm_implementation.address

        def test_is_meta(self, factory, swap):
            assert factory.is_meta(swap.address) is False

        def test_get_pool_types(self, factory, swap, pool_token_types):
            assert factory.get_pool_asset_types(swap.address) == list(pool_token_types)

    @pytest.mark.only_for_pool_type(1)
    class TestMeta:
        @pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
        def test_find_pool_for_coins(self, factory, swap, underlying_tokens, sending, receiving):
            assert (
                factory.find_pool_for_coins(underlying_tokens[sending].address, underlying_tokens[receiving].address)
                == swap.address
            )

        @pytest.mark.parametrize("idx", range(1, 4))
        def test_find_pool_for_coins_underlying(self, factory, swap, underlying_tokens, idx):
            assert factory.find_pool_for_coins(underlying_tokens[0], underlying_tokens[idx]) == swap.address
            assert factory.find_pool_for_coins(underlying_tokens[idx], underlying_tokens[0]) == swap.address

        def test_get_meta_n_coins(self, factory, swap):
            assert factory.get_meta_n_coins(swap.address) == (2, 4)

        def test_get_underlying_coins(self, factory, swap, underlying_tokens):
            tokens = [underlying_tokens[0]] + underlying_tokens[2:]
            assert factory.get_underlying_coins(swap.address) == [t.address for t in tokens]

        def test_get_underlying_decimals(self, factory, swap, base_pool_decimals, pool_type):
            assert factory.get_underlying_decimals(swap.address) == [18] + base_pool_decimals

        def test_get_metapool_rates(self, factory, swap, base_pool, initial_setup):
            assert factory.get_metapool_rates(swap.address) == [10**18, base_pool.get_virtual_price()]

        def test_get_underlying_balances(self, factory, swap, base_pool, initial_setup):
            assert factory.get_metapool_rates(swap.address) == [10**18, base_pool.get_virtual_price()]

        @pytest.mark.parametrize("sending,receiving", itertools.permutations(range(1, 4), 2))
        def test_find_pool_underlying_base_pool_only(
            self, factory, underlying_tokens, sending, receiving, zero_address
        ):
            assert factory.find_pool_for_coins(underlying_tokens[sending], underlying_tokens[receiving]) == zero_address

        @pytest.mark.parametrize("sending,receiving", itertools.permutations(range(2, 5), 2))
        def test_get_coin_indices_underlying(self, factory, swap, sending, receiving, underlying_tokens):
            i, j, is_underlying = factory.get_coin_indices(
                swap, underlying_tokens[sending], underlying_tokens[receiving]
            )
            assert i == sending - 1
            assert j == receiving - 1
            assert is_underlying is True

        @pytest.mark.parametrize("idx", range(1, 4))
        def test_get_coin_indices_reverts(self, factory, swap, base_pool_lp_token, underlying_tokens, idx):
            with boa.reverts():
                factory.get_coin_indices(swap.address, base_pool_lp_token.address, underlying_tokens[idx])

        def test_get_implementation_address(self, factory, swap, amm_implementation_meta):
            assert factory.get_implementation_address(swap.address) == amm_implementation_meta.address

        def test_is_meta(self, factory, swap):
            assert factory.is_meta(swap.address) is True

    class TestFactoryAddPools:
        @pytest.fixture
        def empty_factory(self, deployer, fee_receiver, owner):
            with boa.env.prank(deployer):
                _factory = boa.load(
                    "contracts/main/CurveStableSwapFactoryNG.vy",
                    fee_receiver,
                    owner,
                )
            return _factory

        @pytest.fixture
        def empty_factory_with_implementations(
            self,
            empty_factory,
            owner,
            gauge_implementation,
            views_implementation,
            math_implementation,
            amm_implementation,
            amm_implementation_meta,
        ):
            with boa.env.prank(owner):
                empty_factory.set_gauge_implementation(gauge_implementation.address)
                empty_factory.set_views_implementation(views_implementation.address)
                empty_factory.set_math_implementation(math_implementation.address)

                empty_factory.set_pool_implementations(0, amm_implementation.address)
                empty_factory.set_metapool_implementations(0, amm_implementation_meta.address)

            return empty_factory

        def test_add_base_pool_already_exists(
            self,
            owner,
            factory,
            add_base_pool,
            base_pool,
            base_pool_lp_token,
            base_pool_tokens,
        ):
            with boa.reverts():
                factory.add_base_pool(
                    base_pool.address,
                    base_pool_lp_token.address,
                    [0] * len(base_pool_tokens),
                    len(base_pool_tokens),
                    sender=owner,
                )

        def test_add_base_pool_only_admin(
            self,
            factory,
            bob,
            base_pool,
            base_pool_lp_token,
            base_pool_tokens,
        ):
            with boa.reverts():
                factory.add_base_pool(
                    base_pool.address,
                    base_pool_lp_token.address,
                    [0] * len(base_pool_tokens),
                    len(base_pool_tokens),
                    sender=bob,
                )

        def test_deploy_plain_pool(
            self, empty_factory_with_implementations, amm_interface, pool_tokens, pool_size, zero_address
        ):
            swap_address = empty_factory_with_implementations.deploy_plain_pool(
                "test",
                "test",
                [t.address for t in pool_tokens],
                2000,
                1000000,
                20000000000,
                866,
                0,
                [0] * pool_size,
                [bytes(b"")] * pool_size,
                [zero_address] * pool_size,
            )
            assert swap_address != zero_address

            swap = amm_interface.at(swap_address)
            assert swap.coins(0) == pool_tokens[0].address
            assert swap.coins(1) == pool_tokens[1].address

            assert swap.A() == 2000
            assert swap.fee() == 1000000

            assert empty_factory_with_implementations.pool_count() == 1
            assert empty_factory_with_implementations.pool_list(0) == swap.address
            assert empty_factory_with_implementations.get_decimals(swap) == [t.decimals() for t in pool_tokens]

        def test_pool_count(
            self,
            empty_factory_with_implementations,
            swap,
            add_base_pool,
            amm_interface,
            set_pool_implementations,
            pool_tokens,
            pool_size,
            zero_address,
        ):
            assert empty_factory_with_implementations.pool_count() == 0

            empty_factory_with_implementations.deploy_plain_pool(
                "test",
                "test",
                [t.address for t in pool_tokens],
                2000,
                1000000,
                20000000000,
                866,
                0,
                [0] * pool_size,
                [bytes(b"")] * pool_size,
                [zero_address] * pool_size,
            )
            assert empty_factory_with_implementations.pool_count() == 1
