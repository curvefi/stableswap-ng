import boa
import pytest


@pytest.fixture
def empty_factory(deployer, fee_receiver, owner):
    with boa.env.prank(deployer):
        _factory = boa.load("contracts/main/CurveStableSwapFactoryNG.vy", fee_receiver, owner)
    return _factory


@pytest.fixture
def empty_factory_with_implementations(
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
    owner, factory, add_base_pool, base_pool, base_pool_lp_token, base_pool_tokens
):
    with boa.reverts():
        factory.add_base_pool(
            base_pool.address,
            base_pool_lp_token.address,
            [0] * len(base_pool_tokens),
            len(base_pool_tokens),
            sender=owner,
        )


def test_add_base_pool_only_admin(factory, bob, base_pool, base_pool_lp_token, base_pool_tokens):
    with boa.reverts():
        factory.add_base_pool(
            base_pool.address,
            base_pool_lp_token.address,
            [0] * len(base_pool_tokens),
            len(base_pool_tokens),
            sender=bob,
        )


def test_deploy_plain_pool(
    empty_factory_with_implementations, amm_deployer, plain_tokens, pool_size, zero_address
):
    swap_address = empty_factory_with_implementations.deploy_plain_pool(
        "test",
        "test",
        [t.address for t in (plain_tokens)],
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

    swap = amm_deployer.at(swap_address)
    assert swap.coins(0) == plain_tokens[0].address
    assert swap.coins(1) == plain_tokens[1].address

    assert swap.A() == 2000
    assert swap.fee() == 1000000

    assert empty_factory_with_implementations.pool_count() == 1
    assert empty_factory_with_implementations.pool_list(0) == swap.address
    assert empty_factory_with_implementations.get_decimals(swap) == [
        t.decimals() for t in (plain_tokens)
    ]


def test_pool_count(
    empty_factory_with_implementations,
    add_base_pool,
    amm_deployer,
    set_pool_implementations,
    pool_tokens,
    pool_size,
    zero_address,
):
    assert empty_factory_with_implementations.pool_count() == 0

    empty_factory_with_implementations.deploy_plain_pool(
        "test",  # name: String[32]
        "test",  # symbol: String[10]
        [t.address for t in pool_tokens],  # coins: address[]
        2000,  # A: uint256
        1000000,  # fee: uint256
        20000000000,  # offpeg_fee_multiplier: uint256
        866,  # ma_exp_time: uint256
        0,  # implementation_idx: uint256
        [0] * pool_size,  # asset_types: uint8[]
        [bytes(b"")] * pool_size,  # method_ids: bytes4[]
        [zero_address] * pool_size,  # oracles: address[]
    )
    assert empty_factory_with_implementations.pool_count() == 1
