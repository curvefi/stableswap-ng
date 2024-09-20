import warnings

import boa
import pytest

from tests.utils.tokens import mint_for_testing

warnings.filterwarnings("ignore")


BASE_N_COINS = 5


@pytest.fixture(scope="module")
def ng_base_pool_decimals():
    return [18] * BASE_N_COINS


@pytest.fixture()
def ng_base_pool_tokens(ng_base_pool_decimals, erc20_deployer):
    return [
        erc20_deployer.deploy(f"tkn{i}", f"tkn{i}", ng_base_pool_decimals[i])
        for i in range(BASE_N_COINS)
    ]


@pytest.fixture()
def meta_token(erc20_deployer):
    return erc20_deployer.deploy("OTA", "OTA", 18)


@pytest.fixture()
def tokens_all(meta_token, ng_base_pool_tokens):
    return [meta_token] + ng_base_pool_tokens


@pytest.fixture()
def ng_base_pool(
    deployer,
    factory,
    ng_base_pool_tokens,
    zero_address,
    amm_deployer,
    set_pool_implementations,
    alice,
):
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

    base_pool = amm_deployer.at(pool)

    amt_to_deposit = 10**18

    for token in ng_base_pool_tokens:
        mint_for_testing(alice, amt_to_deposit, token, False)
        token.approve(base_pool.address, 2**256 - 1, sender=alice)

    out_amount = base_pool.add_liquidity(
        [amt_to_deposit] * len(ng_base_pool_tokens), 0, sender=alice
    )
    assert base_pool.totalSupply() == out_amount
    return base_pool


@pytest.fixture()
def ng_metapool_tokens(meta_token, ng_base_pool):
    return [meta_token, ng_base_pool]


@pytest.fixture()
def add_ng_base_pool(owner, factory, ng_base_pool, ng_base_pool_tokens):
    with boa.env.prank(owner):
        factory.add_base_pool(
            ng_base_pool.address,
            ng_base_pool.address,
            [0] * len(ng_base_pool_tokens),
            len(ng_base_pool_tokens),
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
    asset_type = meta_token.asset_type()
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
            asset_type,  # _asset_type: uint8
            method_id,  # _method_id: bytes4
            oracle,  # _oracle: address
        )

    return meta_deployer.at(pool)


@pytest.fixture()
def zap(meta_zap_ng_deployer):
    return meta_zap_ng_deployer.deploy()


@pytest.fixture()
def swap(zap, empty_swap, charlie, tokens_all):
    to_deposit = 10**18

    for token in tokens_all:
        mint_for_testing(charlie, to_deposit, token, False)
        token.approve(zap.address, 2**256 - 1, sender=charlie)

    out_amount = zap.add_liquidity(
        empty_swap.address, [to_deposit] * len(tokens_all), 0, sender=charlie
    )
    assert out_amount > 0
    assert 0 not in empty_swap.get_balances()
    assert empty_swap.totalSupply() > 0

    return empty_swap


def test_calc_amts_add(zap, swap, charlie, tokens_all, ng_base_pool):
    deposit_amount = 10**18
    for token in tokens_all:
        mint_for_testing(charlie, deposit_amount, token, False)
        token.approve(zap.address, 2**256 - 1, sender=charlie)

    deposit_amounts = [deposit_amount] * len(tokens_all)

    calc_amt_zap = zap.calc_token_amount(swap.address, deposit_amounts, True)
    out_amount = zap.add_liquidity(swap.address, deposit_amounts, 0, sender=charlie)

    assert calc_amt_zap == out_amount


def test_calc_amts_remove_imbalance(
    zap, swap, meta_token, ng_base_pool_tokens, ng_base_pool, charlie, tokens_all
):
    initial_balance = swap.balanceOf(charlie)
    amounts_to_remove = [initial_balance // len(tokens_all)] * len(tokens_all)

    swap.approve(zap, 2**256 - 1, sender=charlie)
    max_burn = swap.balanceOf(charlie)
    zap.remove_liquidity_imbalance(swap, amounts_to_remove, max_burn, sender=charlie)

    # check if charlie received what was wanted:
    for i, token in enumerate(tokens_all):
        assert token.balanceOf(charlie) == amounts_to_remove[i]

    # bob is the only LP, total supply is affected in the same way as his balance
    assert swap.balanceOf(charlie) < initial_balance
    assert swap.balanceOf(charlie) >= initial_balance - max_burn

    assert swap.balanceOf(zap) == 0
    assert swap.balanceOf(charlie) == swap.totalSupply()


def test_calc_amts_remove(
    zap, swap, charlie, tokens_all, meta_token, ng_base_pool, ng_base_pool_tokens
):
    charlie_bal_before = []
    for _t in tokens_all:
        charlie_bal_before.append(_t.balanceOf(charlie))

    charlie_lp_bal_before = swap.balanceOf(charlie)

    with boa.env.anchor():
        amts_received = swap.remove_liquidity(charlie_lp_bal_before, [0, 0], sender=charlie)
        base_amts_received = ng_base_pool.remove_liquidity(
            amts_received[1], [0] * ng_base_pool.N_COINS(), sender=charlie
        )
        total_expected_received = [amts_received[0]] + base_amts_received

    swap.approve(zap, 2**256 - 1, sender=charlie)
    total_received_amount = zap.remove_liquidity(
        swap.address, charlie_lp_bal_before, [0] * len(tokens_all), sender=charlie
    )

    # tokens owned by zap:
    zap_balances = []
    for token in tokens_all:
        zap_balances.append(token.balanceOf(zap))

    charlie_bal_after = []
    for _t in tokens_all:
        charlie_bal_after.append(_t.balanceOf(charlie))

    for i in range(len(tokens_all)):
        assert total_received_amount[i] == total_expected_received[i]


def test_calc_amts_remove_one_meta_coin(
    zap, swap, charlie, tokens_all, meta_token, ng_base_pool, ng_base_pool_tokens
):
    charlie_bal_before = []
    for _t in tokens_all:
        charlie_bal_before.append(_t.balanceOf(charlie))

    lp_to_remove = swap.balanceOf(charlie) // 10
    calc_amt_removed = zap.calc_withdraw_one_coin(swap.address, lp_to_remove, 0, sender=charlie)
    swap.approve(zap, 2**256 - 1, sender=charlie)

    with boa.env.anchor():
        amts_received_swap = swap.remove_liquidity_one_coin(lp_to_remove, 0, 0, sender=charlie)
        assert calc_amt_removed == amts_received_swap

    amts_received_zap = zap.remove_liquidity_one_coin(
        swap.address, lp_to_remove, 0, 0, sender=charlie
    )

    assert amts_received_zap == amts_received_swap


def test_calc_amts_remove_one_base_coin(
    zap, swap, charlie, tokens_all, meta_token, ng_base_pool, ng_base_pool_tokens
):
    charlie_bal_before = []
    for _t in tokens_all:
        charlie_bal_before.append(_t.balanceOf(charlie))

    lp_to_remove = swap.balanceOf(charlie) // 10
    calc_amt_removed = zap.calc_withdraw_one_coin(swap.address, lp_to_remove, 1, sender=charlie)
    swap.approve(zap, 2**256 - 1, sender=charlie)

    with boa.env.anchor():
        amts_received_swap = swap.remove_liquidity_one_coin(lp_to_remove, 1, 0, sender=charlie)
        amts_received_base = ng_base_pool.remove_liquidity_one_coin(
            amts_received_swap, 0, 0, sender=charlie
        )
        assert calc_amt_removed == amts_received_base

    amts_received_zap = zap.remove_liquidity_one_coin(
        swap.address, lp_to_remove, 1, 0, sender=charlie
    )
    assert amts_received_zap == amts_received_base
