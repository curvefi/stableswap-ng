import boa
import pytest
from eth_utils import function_signature_to_4byte_selector


@pytest.fixture(scope="function")
def swap(
    deployer,
    factory,
    weth,
    pool_size,
    pool_type,
    pool_token_types,
    pool_tokens,
    zero_address,
    amm_interface,
    set_pool_implementations,
    underlying_tokens,
    base_pool,
    amm_interface_meta,
    add_base_pool,
    set_metapool_implementations,
):
    oracle_method_id = function_signature_to_4byte_selector("exchangeRate()")
    if pool_type == 0:
        A = 2000
        fee = 1000000
        method_ids = [bytes(b"")] * pool_size
        oracles = [zero_address] * pool_size
        asset_types = []

        for i, t in enumerate(pool_token_types):
            if t == 0:
                A = 2000
                fee = 1000000
                asset_types.append(0)
            elif t == 1:
                A = 1000
                fee = 3000000
                asset_types.append(1)
            elif t == 2:
                A = 1000
                fee = 3000000
                asset_types.append(2)
                method_ids[i] = oracle_method_id
                oracles[i] = pool_tokens[i].address
            elif t == 3:
                A = 500
                fee = 4000000
                asset_types.append(3)

        with boa.env.prank(deployer):
            pool = factory.deploy_plain_pool(
                "test", "test", [t.address for t in pool_tokens], A, fee, 866, 0, asset_types, method_ids, oracles
            )
        return amm_interface.at(pool)

    elif pool_type == 1:
        A = 2000
        fee = 1000000
        method_id = bytes(b"")
        oracle = zero_address
        asset_type = 0  # 0 = Plain, 1 = ETH, 2 = Oracle, 3 = Rebasing
        metapool_token_type = pool_token_types[0]

        if metapool_token_type == 0:
            A = 2000
            fee = 1000000
            asset_type = 0
        elif metapool_token_type == 1:
            A = 1000
            fee = 3000000
            asset_type = 1
        elif metapool_token_type == 2:
            A = 1000
            fee = 3000000
            asset_type = 2
            method_id = oracle_method_id
            oracle = underlying_tokens[0].address

        elif metapool_token_type == 3:
            A = 500
            fee = 4000000
            asset_type = 3

        pool = factory.deploy_metapool(
            base_pool.address,  # _base_pool: address
            "test",  # _name: String[32],
            "test",  # _symbol: String[10],
            underlying_tokens[0].address,  # _coin: address,
            A,  # _A: uint256,
            fee,  # _fee: uint256,
            866,  # _ma_exp_time: uint256,
            0,  # _implementation_idx: uint256 = 0,
            asset_type,  # _asset_type: uint8 = 0,
            method_id,  # _method_id: bytes4 = empty(bytes4),
            oracle,  # _oracle: address = empty(address),
        )

        return amm_interface_meta.at(pool)

    else:
        raise ValueError("Wrong pool type")


# <---------------------   Metapool configuration   --------------------->
@pytest.fixture(scope="function")
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


# <---------------------   Functions   --------------------->
@pytest.fixture(scope="function")
def is_eth_pool(pool_tokens, weth):
    return weth in pool_tokens


def add_base_pool_liquidity(user, base_pool, base_pool_tokens, base_pool_decimals):
    amount = 1_000_000
    with boa.env.prank(user):
        for d, token in zip(base_pool_decimals, base_pool_tokens):
            token._mint_for_testing(user, amount * 10**d)
            token.approve(base_pool.address, 2**256 - 1)
        base_pool.add_liquidity([amount * 10**d for d in base_pool_decimals], 0)


@pytest.fixture(scope="function")
def add_initial_liquidity_owner(
    owner,
    approve_owner,
    mint_owner,
    deposit_amounts,
    swap,
    pool_type,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
    base_pool_lp_token,
):
    if pool_type == 0:
        with boa.env.prank(owner):
            swap.add_liquidity(deposit_amounts, 0)
    else:
        add_base_pool_liquidity(owner, base_pool, base_pool_tokens, base_pool_decimals)
        with boa.env.prank(owner):
            base_pool_lp_token.approve(swap.address, 2**256 - 1)
            swap.add_liquidity(deposit_amounts, 0)


@pytest.fixture(scope="function")
def add_initial_liquidity_alice(
    alice,
    approve_alice,
    mint_alice,
    deposit_amounts,
    swap,
    pool_type,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
    base_pool_lp_token,
):
    if pool_type == 0:
        with boa.env.prank(alice):
            swap.add_liquidity(deposit_amounts, 0)
    else:
        add_base_pool_liquidity(alice, base_pool, base_pool_tokens, base_pool_decimals)
        with boa.env.prank(alice):
            base_pool_lp_token.approve(swap.address, 2**256 - 1)
            swap.add_liquidity(deposit_amounts, 0)


@pytest.fixture(scope="function")
def mint_meta_bob(
    bob,
    mint_bob,
    base_pool,
    base_pool_tokens,
    base_pool_decimals,
):
    add_base_pool_liquidity(bob, base_pool, base_pool_tokens, base_pool_decimals)


@pytest.fixture(scope="function")
def approve_meta_bob(bob, underlying_tokens, swap):
    for token in underlying_tokens[:2]:
        token.approve(swap.address, 2**256 - 1)
