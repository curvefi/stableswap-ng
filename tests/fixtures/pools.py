import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

from tests.constants import POOL_TYPES

ORACLE_METHOD_ID = function_signature_to_4byte_selector("exchangeRate()")
OFFPEG_FEE_MULTIPLIER = 20000000000


@pytest.fixture()
def basic_swap(
    deployer, factory, pool_size, pool_tokens, zero_address, amm_deployer, set_pool_implementations
):
    A = 2000
    fee = 1000000
    method_ids = [b""] * pool_size
    oracles = [zero_address] * pool_size

    for i, token in enumerate(pool_tokens):
        match token.asset_type():
            case 0:  # Plain
                A = 2000
                fee = 1000000
            case 1:  # Oracle
                A = 1000
                fee = 3000000
                method_ids[i] = ORACLE_METHOD_ID
                oracles[i] = token.address
            case 2:  # Rebasing
                A = 500
                fee = 4000000

    with boa.env.prank(deployer):
        ma_exp_time = 866
        implementation_idx = 0
        asset_types = [t.asset_type() for t in pool_tokens]
        coins = [t.address for t in pool_tokens]

        pool = factory.deploy_plain_pool(
            "test",
            "test",
            coins,
            A,
            fee,
            OFFPEG_FEE_MULTIPLIER,
            ma_exp_time,
            implementation_idx,
            asset_types,
            method_ids,
            oracles,
        )
    return amm_deployer.at(pool)


@pytest.fixture()
def meta_swap(
    factory,
    set_metapool_implementations,
    zero_address,
    metapool_token,
    base_pool,
    meta_deployer,
    add_base_pool,
):
    A = 2000
    fee = 1000000
    method_id = bytes(b"")
    oracle = zero_address

    asset_type = metapool_token.asset_type()  # 0 = Plain, 1 = Oracle, 2 = Rebasing

    if asset_type == 0:
        A = 2000
        fee = 1000000

    elif asset_type == 1:
        A = 1000
        fee = 3000000
        method_id = ORACLE_METHOD_ID
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
        OFFPEG_FEE_MULTIPLIER,
        866,  # _ma_exp_time: uint256,
        0,  # _implementation_idx: uint256
        asset_type,  # _asset_type: uint8
        method_id,  # _method_id: bytes4
        oracle,  # _oracle: address
    )

    return meta_deployer.at(pool)


@pytest.fixture()
def swap(request, pool_type, pool_token_types, initial_decimals, metapool_token_type):
    # assert all(
    #     fixture is not None for fixture in (initial_decimals, pool_token_types, metapool_token_type)
    # ), "Fixtures required downstream"
    # Check for metapool_token_type only if pool_type is meta
    if pool_type == POOL_TYPES["meta"]:
        assert metapool_token_type is not None, "metapool_token_type is required for meta pools"
    else:
        # For basic pools, we don't care about metapool_token_type
        metapool_token_type = None

    # Continue with the general logic
    assert all(
        fixture is not None for fixture in (initial_decimals, pool_token_types)
    ), "Fixtures required downstream"

    fixture_name = {POOL_TYPES["basic"]: "basic_swap", POOL_TYPES["meta"]: "meta_swap"}[pool_type]
    return request.getfixturevalue(fixture_name)


# <---------------------   Metapool configuration   --------------------->
@pytest.fixture()
def base_pool(deployer, owner, alice, base_pool_tokens, base_pool_lp_token, base_pool_deployer):
    with boa.env.prank(deployer):
        base_pool = base_pool_deployer.deploy(
            owner,
            [t.address for t in base_pool_tokens],
            base_pool_lp_token.address,
            200,
            3000000,
            5000000000,
        )
        base_pool_lp_token.set_minter(base_pool.address)
    return base_pool
