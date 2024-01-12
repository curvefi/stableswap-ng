import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

oracle_method_id = function_signature_to_4byte_selector("exchangeRate()")
offpeg_fee_multiplier = 20000000000


@pytest.fixture()
def basic_swap(deployer, factory, pool_size, pool_tokens, zero_address, amm_interface):
    A = 2000
    fee = 1000000
    method_ids = [bytes(b"")] * pool_size
    oracles = [zero_address] * pool_size
    asset_types = []

    for i, token in enumerate(pool_tokens):
        asset_type = token.asset_type()

        if asset_type == 0:
            A = 2000
            fee = 1000000
            asset_types.append(asset_type)
        elif asset_type == 1:
            A = 1000
            fee = 3000000
            asset_types.append(asset_type)
            method_ids[i] = oracle_method_id
            oracles[i] = token.address
        elif asset_type == 2:
            A = 500
            fee = 4000000
            asset_types.append(asset_type)

    with boa.env.prank(deployer):
        pool = factory.deploy_plain_pool(
            "test",
            "test",
            [t.address for t in pool_tokens],
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


@pytest.fixture()
def meta_swap(factory, zero_address, underlying_tokens, base_pool, amm_interface_meta):
    A = 2000
    fee = 1000000
    method_id = bytes(b"")
    oracle = zero_address

    metapool_token = underlying_tokens[0]
    asset_type = metapool_token.asset_type()  # 0 = Plain, 1 = Oracle, 2 = Rebasing

    if asset_type == 0:
        A = 2000
        fee = 1000000

    elif asset_type == 1:
        A = 1000
        fee = 3000000
        method_id = oracle_method_id
        oracle = metapool_token.address

    elif asset_type == 2:
        A = 500
        fee = 4000000

    pool = factory.deploy_metapool(
        base_pool.address,  # _base_pool: address
        "test",  # _name: String[32],
        "test",  # _symbol: String[10],
        metapool_token.address,  # _coin: address,
        A,  # _A: uint256,
        fee,  # _fee: uint256,
        offpeg_fee_multiplier,
        866,  # _ma_exp_time: uint256,
        0,  # _implementation_idx: uint256
        asset_type,  # _asset_type: uint8
        method_id,  # _method_id: bytes4
        oracle,  # _oracle: address
    )

    return amm_interface_meta.at(pool)


@pytest.fixture()
def swap(basic_swap, meta_swap, pool_type):
    return {0: basic_swap, 1: meta_swap}[pool_type]


# <---------------------   Metapool configuration   --------------------->
@pytest.fixture()
def base_pool(deployer, owner, alice, base_pool_decimals, base_pool_tokens, base_pool_lp_token, zero_address):
    with boa.env.prank(deployer):
        base_pool = boa.load(
            "contracts/mocks/CurvePool.vy",
            owner,
            [t.address for t in base_pool_tokens],
            base_pool_lp_token.address,
            200,
            3000000,
            5000000000,
        )
        base_pool_lp_token.set_minter(base_pool.address)
    return base_pool
