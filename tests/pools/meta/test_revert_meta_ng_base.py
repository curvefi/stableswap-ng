import boa
import pytest


@pytest.fixture(scope="module")
def borky_factory(
    deployer,
    fee_receiver,
    owner,
    gauge_implementation,
    views_implementation,
    math_implementation,
    amm_implementation,
    amm_implementation_meta,
):
    with boa.env.prank(deployer):
        _factory = boa.load(
            "contracts/main/CurveStableSwapFactoryNG.vy",
            fee_receiver,
            owner,
        )

    with boa.env.prank(owner):
        _factory.set_gauge_implementation(gauge_implementation.address)
        _factory.set_views_implementation(views_implementation.address)
        _factory.set_math_implementation(math_implementation.address)
        _factory.set_pool_implementations(0, amm_implementation.address)
        _factory.set_metapool_implementations(0, amm_implementation_meta.address)

    return _factory


# <---------------------   Functions   --------------------->


@pytest.fixture(scope="module")
def ng_base_pool_decimals():
    return [18, 18]


@pytest.fixture(scope="module")
def ng_base_pool_tokens(deployer, ng_base_pool_decimals):
    tokens = []
    with boa.env.prank(deployer):
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "DAI", "DAI", ng_base_pool_decimals[0]))
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "USDC", "USDC", ng_base_pool_decimals[1]))

    return tokens


@pytest.fixture(scope="module")
def ng_base_pool(
    deployer,
    borky_factory,
    ng_base_pool_tokens,
    zero_address,
    amm_interface,
):
    asset_types = [0, 0]
    pool_size = len(ng_base_pool_tokens)
    offpeg_fee_multiplier = 20000000000
    method_ids = [bytes(b"")] * pool_size
    oracles = [zero_address] * pool_size
    A = 1000
    fee = 3000000

    with boa.env.prank(deployer):
        pool = borky_factory.deploy_plain_pool(
            "test",
            "test",
            [t.address for t in ng_base_pool_tokens],
            A,
            fee,
            offpeg_fee_multiplier,
            866,
            0,
            asset_types,
            method_ids,
            oracles,
        )

    return amm_interface.at(pool)


@pytest.fixture(scope="module")
def add_ng_base_pool(
    owner,
    borky_factory,
    ng_base_pool,
    ng_base_pool_tokens,
):
    with boa.env.prank(owner):
        borky_factory.add_base_pool(
            ng_base_pool.address,
            ng_base_pool.address,
            [0] * len(ng_base_pool_tokens),
            len(ng_base_pool_tokens),
        )


def test_revert_metapool_deployment_with_ng_base_pool(
    deployer, borky_factory, zero_address, add_ng_base_pool, ng_base_pool
):
    method_id = bytes(b"")
    oracle = zero_address
    offpeg_fee_multiplier = 20000000000
    A = 1000
    fee = 3000000
    meta_token = boa.load(
        "contracts/mocks/ERC20.vy",
        "OTA",
        "OTA",
        18,
    )
    asset_type = meta_token.asset_type()

    with boa.reverts():
        borky_factory.deploy_metapool(
            ng_base_pool.address,  # _base_pool: address
            "test",  # _name: String[32],
            "test",  # _symbol: String[10],
            meta_token.address,  # _coin: address,
            A,  # _A: uint256,
            fee,  # _fee: uint256,
            offpeg_fee_multiplier,
            866,  # _ma_exp_time: uint256,
            0,  # _implementation_idx: uint256
            asset_type,  # _asset_type: uint8
            method_id,  # _method_id: bytes4
            oracle,  # _oracle: address
            sender=deployer,
        )
