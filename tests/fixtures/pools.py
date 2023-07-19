import boa
import pytest
from eth_utils import function_signature_to_4byte_selector


# Only initialize useful fixtures
@pytest.fixture(scope="module")
def empty_swap(
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
        return amm_interface_plain.at(pool)

    elif pool_type == 1:
        base_pool = request.getfixturevalue("base_pool")
        underlying_tokens = request.getfixturevalue("underlying_tokens")
        amm_interface_meta = request.getfixturevalue("amm_interface_meta")
        _ = request.getfixturevalue("add_base_pool")
        _ = request.getfixturevalue("set_metapool_implementations")

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
@pytest.fixture(scope="module")
def base_pool(deployer, owner, alice, base_pool_decimals, base_pool_tokens, base_pool_lp_token):

    # TODO: depending on base_pool_decimals, choose pool config (2-coin or 3-coin)
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


@pytest.fixture(scope="module")
def swap(
    empty_swap,
    pool_type,
    deposit_amounts,
    mint_alice,
    approve_alice,
    alice,
    underlying_decimals,
    underlying_tokens,
    underlying_precisions,
    base_pool,
    base_pool_lp_token,
):

    if pool_type == 0:

        with boa.env.prank(alice):
            empty_swap.add_liquidity(deposit_amounts, 0)

    elif pool_type == 1:

        amount = 1_000_000
        if not base_pool.balances(0) >= amount * underlying_precisions[2]:
            with boa.env.prank(alice):
                for d, token in zip(underlying_decimals[2:], underlying_tokens[2:]):
                    token._mint_for_testing(alice, amount * 10**d)
                    token.approve(base_pool.address, 2**256 - 1)

                base_pool.add_liquidity([amount * 10**d for d in underlying_decimals[2:]], 0)

        # add liquidity to the metapool next:
        amounts = [amount * underlying_precisions[0], underlying_tokens[1].balanceOf(alice)]

        for _amt in amounts:
            # this only fails if there are isolation issues
            # if the above fails: alice deposits into base pool, and then deposits lp
            # token into metapool. if metapool gets wiped: her lp tokens are gone forever.
            # so base pool will have non-zero liquidity, but alice will have no lp tokens and
            # metapool will be empty!
            if _amt == 0:  # <--- it shouldnt be empty!
                # the following asserts show that base pool has liquidity, metapool is empty
                assert empty_swap.get_balances() == [0, 0]
                assert empty_swap.balanceOf(alice) == 0
                assert base_pool_lp_token == underlying_tokens[1]
                assert base_pool_lp_token.balanceOf(alice) == 0

                assert base_pool.balances(0) == 0  # this will fail

        with boa.env.prank(alice):

            for coin in underlying_tokens:
                coin.approve(empty_swap, 2**256 - 1)

            empty_swap.add_liquidity(amounts, 0)

    return empty_swap


# <---------------------   Functions   --------------------->


@pytest.fixture(scope="module")
def is_eth_pool(pool_tokens, weth):
    return weth in pool_tokens
