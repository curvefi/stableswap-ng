import itertools

import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

from tests.utils import get_asset_types_in_pool
from tests.utils.tokens import mint_for_testing


def mint_vault_tokens(deposit_amount, underlying_token, vault_contract, user):
    mint_for_testing(user, deposit_amount, underlying_token, False)
    underlying_token.approve(vault_contract, 2**256 - 1, sender=user)
    vault_contract.deposit(deposit_amount, user, sender=user)
    return vault_contract.balanceOf(user)


def donate_to_vault(donation_amount, underlying_token, vault_contract, user):
    donation_amount = donation_amount * 10 ** underlying_token.decimals()
    mint_for_testing(user, donation_amount, underlying_token, False)
    underlying_token.transfer(vault_contract, donation_amount, sender=user)


def mint_tokens(charlie, pool_erc20_tokens, pool_tokens, swap, i):
    amount_erc20_in = 10 ** pool_erc20_tokens[i].decimals()

    if amount_erc20_in > pool_erc20_tokens[i].balanceOf(charlie):
        if i != 0:
            bal_before = pool_erc20_tokens[i].balanceOf(charlie)
            mint_for_testing(charlie, amount_erc20_in, pool_erc20_tokens[i], False)
            amount_in = pool_erc20_tokens[i].balanceOf(charlie) - bal_before
        else:
            amount_in = mint_vault_tokens(
                amount_erc20_in, pool_erc20_tokens[0], pool_tokens[0], charlie
            )

    pool_tokens[i].approve(swap, 2**256 - 1, sender=charlie)

    return amount_in


@pytest.fixture()
def asset(deployer, erc20_deployer):
    with boa.env.prank(deployer):
        return erc20_deployer.deploy("Asset", "AST", 8)  # 8 decimals


@pytest.fixture()
def token_a(deployer, asset, erc4626_deployer):
    with boa.env.prank(deployer):
        return erc4626_deployer.deploy("Vault", "VLT", 18, asset.address)  # 8 decimals


@pytest.fixture()
def token_b(deployer, erc20oracle_deployer):
    with boa.env.prank(deployer):
        return erc20oracle_deployer.deploy("Oracle", "ORC", 18, 1006470359024000000)


@pytest.fixture()
def token_c(deployer, erc20rebasing_conditional_deployer):
    with boa.env.prank(deployer):
        return erc20rebasing_conditional_deployer.deploy("Rebasing", "RBSN", 6, True)


@pytest.fixture()
def pool_tokens(token_a, token_b, token_c):
    return [token_a, token_b, token_c]


@pytest.fixture()
def pool_erc20_tokens(asset, token_b, token_c):
    return [asset, token_b, token_c]


@pytest.fixture()
def asset_types(pool_tokens):
    _asset_types = []
    for token in pool_tokens:
        if "ERC20Oracle" in token.filename:
            _asset_types.append(1)
        elif "ERC20Rebasing" in token.filename:
            _asset_types.append(2)
        elif "ERC4626" in token.filename:
            _asset_types.append(3)
        else:
            _asset_types.append(0)
    return _asset_types


@pytest.fixture()
def empty_swap(
    deployer,
    factory,
    pool_tokens,
    zero_address,
    amm_deployer,
    asset_types,
    set_pool_implementations,
):
    pool_size = len(pool_tokens)
    oracle_method_id = function_signature_to_4byte_selector("exchangeRate()")
    offpeg_fee_multiplier = 20000000000
    method_ids = [bytes(b"")] * pool_size
    oracles = [zero_address] * pool_size
    A = 1000
    fee = 3000000

    for i in range(pool_size):
        if asset_types[i] == 1:
            method_ids[i] = oracle_method_id
            oracles[i] = pool_tokens[i].address

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

    return amm_deployer.at(pool)


@pytest.fixture()
def deposit_amounts(pool_erc20_tokens, token_a, bob):
    _deposit_amounts = []
    for i, token in enumerate(pool_erc20_tokens):
        _deposit_amount = 10**6 * 10 ** token.decimals()
        if token.balanceOf(bob) < _deposit_amount:
            mint_for_testing(bob, _deposit_amount, token, False)

        if i == 0:  # erc4626 token
            _deposit_amount = mint_vault_tokens(_deposit_amount, token, token_a, bob)

        _deposit_amounts.append(_deposit_amount)

        try:
            assert token.balanceOf(bob) == _deposit_amount
        except:  # noqa: E722
            mint_for_testing(bob, _deposit_amount, token, False)
            assert token.balanceOf(bob) == _deposit_amount

    return _deposit_amounts


@pytest.fixture()
def swap(empty_swap, bob, deposit_amounts, pool_tokens):
    for token in pool_tokens:
        token.approve(empty_swap, 2**256 - 1, sender=bob)
    empty_swap.add_liquidity(deposit_amounts, 0, bob, sender=bob)
    return empty_swap


@pytest.mark.parametrize("i,j", itertools.permutations(range(3), 2))
def test_swap(swap, i, j, charlie, pool_tokens, pool_erc20_tokens):
    amount_in = mint_tokens(charlie, pool_erc20_tokens, pool_tokens, swap, i)

    if "RebasingConditional" in pool_tokens[i].filename:
        pool_tokens[i].rebase()
        assert 2 in get_asset_types_in_pool(swap)

    calculated = swap.get_dy(i, j, amount_in)
    dy = swap.exchange(i, j, amount_in, int(0.99 * calculated), sender=charlie)

    try:
        assert dy == calculated
    except:  # noqa: E722
        assert 2 in [i, j]  # rebasing token balances can have wonky math
        assert dy == pytest.approx(calculated)


@pytest.mark.parametrize("i,j", itertools.permutations(range(3), 2))
def test_donate_swap(swap, i, j, alice, charlie, pool_tokens, pool_erc20_tokens):
    amount_in = mint_tokens(charlie, pool_erc20_tokens, pool_tokens, swap, i)

    # rebase:
    if "RebasingConditional" in pool_tokens[i].filename:
        pool_tokens[i].rebase()

    # donate to vault:
    donate_to_vault(10**5, pool_erc20_tokens[0], pool_tokens[0], alice)

    # calculate expected output and swap:
    calculated = swap.get_dy(i, j, amount_in)
    dy = swap.exchange(i, j, amount_in, int(0.99 * calculated), sender=charlie)

    # check:
    try:
        assert dy == calculated
    except:  # noqa: E722
        assert 2 in [i, j]  # rebasing token balances can have wonky math
        assert dy == pytest.approx(calculated)


def test_rebase(swap, charlie, bob, pool_tokens):
    amount_rewards = 10**4 * 10**18
    i = 1
    if amount_rewards > pool_tokens[i].balanceOf(charlie):
        mint_for_testing(charlie, amount_rewards, pool_tokens[i], False)

    pool_tokens[i].transfer(swap, amount_rewards, sender=charlie)  # <---- donate.
    bob_lp_tokens = swap.balanceOf(bob)
    swap.remove_liquidity(bob_lp_tokens, [0, 0, 0], sender=bob)  # <--- should not revert
