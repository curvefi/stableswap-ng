import warnings

import boa
import pytest

from tests.utils.tokens import mint_for_testing

warnings.filterwarnings("ignore")


@pytest.fixture()
def meta_token(deployer, erc20_deployer):
    with boa.env.prank(deployer):
        return erc20_deployer.deploy("OTA", "OTA", 18)


@pytest.fixture()
def metapool_tokens(meta_token, base_pool):
    return [meta_token, base_pool]


@pytest.fixture()
def tokens_all(meta_token, base_pool_tokens):
    return [meta_token] + base_pool_tokens


@pytest.fixture()
def add_base_pool(owner, factory, base_pool, base_pool_lp_token, base_pool_tokens):
    with boa.env.prank(owner):
        factory.add_base_pool(
            base_pool.address,
            base_pool_lp_token.address,
            [0] * len(base_pool_tokens),
            len(base_pool_tokens),
        )


@pytest.fixture()
def empty_swap(
    deployer,
    factory,
    zero_address,
    meta_token,
    base_pool,
    meta_deployer,
    add_base_pool,
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
            base_pool.address,  # _base_pool: address
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
def zap(base_pool, base_pool_tokens, base_pool_lp_token, zap_deployer):
    return zap_deployer.deploy(
        base_pool.address, base_pool_lp_token.address, [a.address for a in base_pool_tokens]
    )


@pytest.fixture()
def initial_amts():
    return [100 * 10**18] * 4


@pytest.fixture()
def swap(zap, base_pool, empty_swap, charlie, tokens_all, initial_amts):
    for i in range(3):
        assert base_pool.balances(i) == 0

    for token in tokens_all:
        mint_for_testing(charlie, initial_amts[0], token, False)
        token.approve(zap.address, 2**256 - 1, sender=charlie)

    out_amount = zap.add_liquidity(empty_swap.address, initial_amts, 0, sender=charlie)
    assert out_amount > 0
    assert 0 not in empty_swap.get_balances()
    assert empty_swap.totalSupply() > 0

    return empty_swap


def test_calc_amts_add(zap, swap, charlie, tokens_all):
    deposit_amount = 2 * 100 * 10**18

    for token in tokens_all:
        mint_for_testing(charlie, deposit_amount, token, False)
        token.approve(zap.address, 2**256 - 1, sender=charlie)

    deposit_amounts = [deposit_amount] * 4

    calc_amt_zap = zap.calc_token_amount(swap.address, deposit_amounts, True)
    out_amount = zap.add_liquidity(swap.address, deposit_amounts, 0, sender=charlie)

    assert calc_amt_zap == out_amount


def test_calc_amts_remove_imbalance(
    zap,
    swap,
    meta_token,
    base_pool_tokens,
    base_pool_lp_token,
    base_pool,
    charlie,
    tokens_all,
    initial_amts,
):
    amounts = [i // 4 for i in initial_amts]
    initial_balance = swap.balanceOf(charlie)
    swap.approve(zap, 2**256 - 1, sender=charlie)
    max_burn = swap.balanceOf(charlie)
    zap.remove_liquidity_imbalance(swap, amounts, max_burn, sender=charlie)

    # check if charlie received what was wanted:
    for i, token in enumerate(tokens_all):
        assert token.balanceOf(charlie) == amounts[i]

    # bob is the only LP, total supply is affected in the same way as his balance
    assert swap.balanceOf(charlie) < initial_balance
    assert swap.balanceOf(charlie) >= initial_balance - max_burn

    assert swap.balanceOf(zap) == 0
    assert swap.balanceOf(charlie) == swap.totalSupply()


def test_calc_amts_remove(zap, swap, charlie, tokens_all, meta_token, base_pool, base_pool_tokens):
    charlie_bal_before = []
    for _t in tokens_all:
        charlie_bal_before.append(_t.balanceOf(charlie))

    charlie_lp_bal_before = swap.balanceOf(charlie)

    with boa.env.anchor():
        amts_received = swap.remove_liquidity(charlie_lp_bal_before, [0, 0], sender=charlie)
        base_amts_received = base_pool.remove_liquidity(amts_received[1], [0, 0, 0], sender=charlie)
        total_expected_received = [amts_received[0]] + base_amts_received

    total_token_balances = [meta_token.balanceOf(swap)] + [
        _t.balanceOf(base_pool) for _t in base_pool_tokens
    ]

    swap.approve(zap, 2**256 - 1, sender=charlie)
    total_received_amount = zap.remove_liquidity(
        swap.address, charlie_lp_bal_before, [0] * 4, sender=charlie
    )

    # tokens owned by zap:
    zap_balances = []
    for token in tokens_all:
        zap_balances.append(token.balanceOf(zap))

    charlie_bal_after = []
    for _t in tokens_all:
        charlie_bal_after.append(_t.balanceOf(charlie))

    for i in range(len(tokens_all)):
        assert total_token_balances[i] == total_received_amount[i] == total_expected_received[i]
