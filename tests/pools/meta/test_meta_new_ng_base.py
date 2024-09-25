import itertools

import boa
import pytest

from tests.utils.tokens import mint_for_testing

BASE_N_COINS = 5


@pytest.fixture(scope="module")
def ng_base_pool_decimals():
    return [18] * BASE_N_COINS


@pytest.fixture()
def ng_base_pool_tokens(ng_base_pool_decimals, erc20_deployer):
    return [erc20_deployer.deploy(f"tkn{i}", f"tkn{i}", ng_base_pool_decimals[i]) for i in range(BASE_N_COINS)]


@pytest.fixture()
def meta_token(erc20_deployer):
    return erc20_deployer.deploy("OTA", "OTA", 18)


@pytest.fixture()
def ng_base_pool(deployer, factory, ng_base_pool_tokens, zero_address, amm_deployer, set_pool_implementations):
    pool_size = len(ng_base_pool_tokens)
    offpeg_fee_multiplier = 20000000000
    method_ids = [bytes(b"")] * pool_size
    oracles = [zero_address] * pool_size
    A = 1000
    fee = 3000000

    with boa.env.prank(deployer):
        pool = factory.deploy_plain_pool(
            "test",
            "test",
            [t.address for t in ng_base_pool_tokens],
            A,
            fee,
            offpeg_fee_multiplier,
            866,
            0,
            [tkn.asset_type() for tkn in ng_base_pool_tokens],
            method_ids,
            oracles,
        )

    return amm_deployer.at(pool)


@pytest.fixture()
def ng_metapool_tokens(meta_token, ng_base_pool):
    return [meta_token, ng_base_pool]


@pytest.fixture()
def add_ng_base_pool(owner, factory, ng_base_pool, ng_base_pool_tokens):
    with boa.env.prank(owner):
        factory.add_base_pool(
            ng_base_pool.address, ng_base_pool.address, [0] * len(ng_base_pool_tokens), len(ng_base_pool_tokens)
        )


@pytest.fixture()
def empty_swap(
    deployer,
    factory,
    zero_address,
    meta_token,
    ng_base_pool,
    meta_deployer,
    add_ng_base_pool,
    set_metapool_implementations,
):
    method_id = bytes(b"")
    oracle = zero_address
    offpeg_fee_multiplier = 20000000000
    A = 1000
    fee = 3000000

    with boa.env.prank(deployer):
        pool = factory.deploy_metapool(
            ng_base_pool.address,  # _base_pool: address
            "test",  # _name: String[32],
            "test",  # _symbol: String[10],
            meta_token.address,  # _coin: address,
            A,  # _A: uint256,
            fee,  # _fee: uint256,
            offpeg_fee_multiplier,
            866,  # _ma_exp_time: uint256,
            0,  # _implementation_idx: uint256
            meta_token.asset_type(),  # _asset_type: uint8
            method_id,  # _method_id: bytes4
            oracle,  # _oracle: address
        )

    return meta_deployer.at(pool)


@pytest.fixture()
def mint_and_approve_for_bob(meta_token, ng_base_pool_tokens, bob, empty_swap, ng_base_pool):
    for token in [meta_token] + ng_base_pool_tokens:
        mint_for_testing(bob, 10**25, token)
        token.approve(empty_swap, 2**256 - 1, sender=bob)
        token.approve(ng_base_pool, 2**256 - 1, sender=bob)


@pytest.fixture()
def deposit_amounts(
    meta_token, ng_base_pool, ng_base_pool_tokens, ng_base_pool_decimals, empty_swap, bob, mint_and_approve_for_bob
):
    _deposit_amounts = []
    INITIAL_AMOUNT = 1_000_000 * BASE_N_COINS
    _deposit_amounts.append(INITIAL_AMOUNT // BASE_N_COINS * 10 ** meta_token.decimals())

    def add_base_pool_liquidity(user, base_pool, base_pool_tokens, base_pool_decimals):
        amount = INITIAL_AMOUNT // BASE_N_COINS
        with boa.env.prank(user):
            amounts = [amount * 10**d for d in base_pool_decimals]
            base_pool.add_liquidity(amounts, 0)

    add_base_pool_liquidity(bob, ng_base_pool, ng_base_pool_tokens, ng_base_pool_decimals)
    _deposit_amounts.append(INITIAL_AMOUNT // BASE_N_COINS * 10 ** ng_base_pool.decimals())
    ng_base_pool.approve(empty_swap, 2**256 - 1, sender=bob)
    return _deposit_amounts


@pytest.fixture()
def swap(empty_swap, bob, deposit_amounts):
    empty_swap.add_liquidity(deposit_amounts, 0, bob, sender=bob)
    return empty_swap


@pytest.mark.parametrize("sending,receiving", itertools.permutations(range(4), 2))
def test_exchange_underlying_ng_base(swap, bob, sending, receiving):
    amount = 10**19
    expected_out = swap.get_dy_underlying(sending, receiving, amount)
    actual_out = swap.exchange_underlying(sending, receiving, amount, 0, sender=bob)

    assert expected_out == actual_out
    assert expected_out == actual_out
