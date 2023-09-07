import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

from tests.utils.tokens import mint_for_testing


@pytest.fixture(scope="module")
def token_a(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/mocks/ERC20Oracle.vy",
            "OTA",
            "OTA",
            18,
            1006470359024000000,
        )


@pytest.fixture(scope="module")
def token_b(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/mocks/ERC20Oracle.vy",
            "OTB",
            "OTB",
            18,
            1000000000000000000,
        )


@pytest.fixture(scope="module")
def token_c(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/mocks/ERC20.vy",
            "OTC",
            "OTC",
            18,
        )


@pytest.fixture(scope="module")
def pool_tokens(token_a, token_b, token_c):
    return [token_a, token_b, token_c]


@pytest.fixture(scope="module")
def asset_types(pool_tokens):
    _asset_types = []
    for token in pool_tokens:
        if "ERC20Oracle" in token.filename:
            _asset_types.append(1)
        elif "ERC20Rebasing" in token.filename:
            _asset_types.append(2)
        else:
            _asset_types.append(0)
    return _asset_types


@pytest.fixture(scope="module")
def empty_swap(
    deployer,
    factory,
    pool_tokens,
    zero_address,
    amm_interface,
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

    return amm_interface.at(pool)


@pytest.fixture(scope="module")
def deposit_amounts(pool_tokens, bob):
    _deposit_amounts = []
    for i, token in enumerate(pool_tokens):
        _deposit_amount = 10**6 * 10 ** token.decimals()
        if token.balanceOf(bob) < _deposit_amount:
            mint_for_testing(bob, _deposit_amount, token, False)

        _deposit_amounts.append(_deposit_amount)
    return _deposit_amounts


@pytest.fixture(scope="module")
def swap(empty_swap, bob, deposit_amounts, pool_tokens):

    for token in pool_tokens:
        token.approve(empty_swap, 2**256 - 1, sender=bob)

    empty_swap.add_liquidity(deposit_amounts, 0, bob, sender=bob)
    return empty_swap


def test_swap(swap, charlie, pool_tokens):

    amount_in = 10**18
    i = 0
    j = 1
    if amount_in > pool_tokens[i].balanceOf(charlie):
        mint_for_testing(charlie, 10**18, pool_tokens[i], False)

    pool_tokens[i].approve(swap, 2**256 - 1, sender=charlie)
    swap.exchange(i, j, amount_in, 0, sender=charlie)
