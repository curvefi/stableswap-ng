import boa
import pytest
from eth_utils import function_signature_to_4byte_selector


# Only initialize useful fixtures
@pytest.fixture(scope="module")
def swap(
    request,
    deployer,
    factory,
    weth,
    pool_size,
    pool_type,
    pool_token_types,
    pool_tokens,
    zero_address,
):
    oracle_method_id = function_signature_to_4byte_selector("exchangeRate()")
    if pool_type == 0:
        amm_interface_plain = request.getfixturevalue("amm_interface")
        _ = request.getfixturevalue("set_pool_implementations")

        A = 2000
        fee = 1000000
        method_ids = [bytes(b"")] * pool_size
        oracles = [zero_address] * pool_size
        asset_type = []
        is_rebasing = [False] * pool_size

        for i, t in enumerate(pool_token_types):
            if t == 0:
                A = 2000
                fee = 1000000
                asset_type.append(0)
            elif t == 1:
                A = 1000
                fee = 3000000
                asset_type.append(1)
            elif t == 2:
                A = 1000
                fee = 3000000
                asset_type.append(2)
                method_ids[i] = oracle_method_id
                oracles[i] = pool_tokens[i].address
            elif t == 3:
                A = 500
                fee = 4000000
                asset_type.append(3)
                is_rebasing[i] = True

        with boa.env.prank(deployer):
            pool = factory.deploy_plain_pool(
                "test",
                "test",
                [t.address for t in pool_tokens],
                A,
                fee,
                866,
                0,
                method_ids,
                oracles,
                asset_type,
                is_rebasing,
            )
        return amm_interface_plain.at(pool)

    elif pool_type == 1:
        base_pool = request.getfixturevalue("base_pool")
        underlying_tokens = request.getfixturevalue("underlying_tokens")
        amm_interface_meta = request.getfixturevalue("amm_interface")
        _ = request.getfixturevalue("add_base_pool")
        _ = request.getfixturevalue("set_pool_implementations")

        A = 2000
        fee = 1000000
        method_id = bytes(b"")
        oracle = zero_address
        asset_type = 0  # 0 = Plain, 1 = ETH, 2 = Oracle, 3 = Rebasing
        is_rebasing = False
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
            is_rebasing = True

        pool = factory.deploy_metapool(
            base_pool.address,
            "test",
            "test",
            underlying_tokens[0].address,
            A,
            fee,
            866,
            0,
            0,
            method_id,
            oracle,
            is_rebasing,
        )

        return amm_interface_meta.at(pool)

    else:
        raise ValueError("Wrong pool type")


# <---------------------   Metapool configuration   --------------------->
@pytest.fixture(scope="module")
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

    amount = 1_000_000
    with boa.env.prank(alice):
        for d, token in zip(base_pool_decimals, base_pool_tokens):
            token._mint_for_testing(alice, amount * 10**d)
            token.approve(base_pool.address, 2**256 - 1)

        base_pool.add_liquidity([amount * 10**d for d in base_pool_decimals], 0)
        base_pool_lp_token.transfer(zero_address, base_pool_lp_token.balanceOf(alice))

    return base_pool


# <---------------------   Functions   --------------------->
@pytest.fixture(scope="module")
def is_eth_pool(pool_tokens, weth):
    return weth in pool_tokens


@pytest.fixture(scope="module")
def add_initial_liquidity(owner, approve_owner, mint_owner, deposit_amounts, swap):
    with boa.env.prank(owner):
        swap.add_liquidity(deposit_amounts, 0)


@pytest.fixture(scope="module")
def add_initial_liquidity_alice(alice, approve_alice, mint_alice, deposit_amounts, swap):
    with boa.env.prank(alice):
        swap.add_liquidity(deposit_amounts, 0)
