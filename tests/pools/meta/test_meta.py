import boa
import pytest

from tests.utils.tokens import mint_for_testing


@pytest.fixture(scope="module")
def base_pool_decimals():
    return [18, 18, 18]


@pytest.fixture(scope="module")
def base_pool_tokens(deployer, base_pool_decimals):
    tokens = []
    with boa.env.prank(deployer):
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "DAI", "DAI", base_pool_decimals[0]))
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "USDC", "USDC", base_pool_decimals[1]))
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "USDT", "USDT", base_pool_decimals[2]))

    return tokens


@pytest.fixture(scope="module")
def meta_token(deployer):
    with boa.env.prank(deployer):
        return boa.load(
            "contracts/mocks/ERC20.vy",
            "OTA",
            "OTA",
            18,
        )


@pytest.fixture(scope="module")
def asset_types():
    _asset_types = [0, 0, 0]
    return _asset_types


@pytest.fixture(scope="module")
def base_pool(
    deployer,
    factory,
    base_pool_tokens,
    zero_address,
    amm_interface,
    asset_types,
    set_pool_implementations,
):
    pool_size = len(base_pool_tokens)
    offpeg_fee_multiplier = 20000000000
    method_ids = [bytes(b"")] * pool_size
    oracles = [zero_address] * pool_size
    A = 1000
    fee = 3000000

    with boa.env.prank(deployer):
        pool = factory.deploy_plain_pool(
            "test",
            "test",
            [t.address for t in base_pool_tokens],
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
def metapool_tokens(meta_token, base_pool):
    return [meta_token, base_pool]


@pytest.fixture(scope="module")
def add_base_pool(
    owner,
    factory,
    base_pool,
    base_pool_tokens,
):
    with boa.env.prank(owner):
        factory.add_base_pool(
            base_pool.address,
            base_pool.address,
            [0] * len(base_pool_tokens),
            len(base_pool_tokens),
        )


@pytest.fixture(scope="module")
def empty_swap(
    deployer,
    factory,
    zero_address,
    meta_token,
    base_pool,
    amm_interface_meta,
    asset_types,
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

    return amm_interface_meta.at(pool)


@pytest.fixture(scope="module")
def deposit_amounts(meta_token, bob, base_pool, base_pool_tokens, base_pool_decimals, empty_swap):
    _deposit_amounts = []
    INITIAL_AMOUNT = 3_000_000

    _deposit_amount = INITIAL_AMOUNT // 3 * 10 ** meta_token.decimals()
    if meta_token.balanceOf(bob) < _deposit_amount:
        mint_for_testing(bob, _deposit_amount, meta_token, False)
        _deposit_amounts.append(_deposit_amount)

    def add_base_pool_liquidity(user, base_pool, base_pool_tokens, base_pool_decimals):
        amount = INITIAL_AMOUNT // 3
        with boa.env.prank(user):
            for d, token in zip(base_pool_decimals, base_pool_tokens):
                token._mint_for_testing(user, amount * 10**d)
                token.approve(base_pool.address, 2**256 - 1)

            amounts = [amount * 10**d for d in base_pool_decimals]
            base_pool.add_liquidity(amounts, 0)

    add_base_pool_liquidity(bob, base_pool, base_pool_tokens, base_pool_decimals)
    _deposit_amounts.append(INITIAL_AMOUNT // 3 * 10 ** base_pool.decimals())

    return _deposit_amounts


@pytest.fixture(scope="module")
def swap(empty_swap, bob, deposit_amounts, metapool_tokens):
    for token in metapool_tokens:
        token.approve(empty_swap.address, 2**256 - 1, sender=bob)
    empty_swap.add_liquidity(deposit_amounts, 0, bob, sender=bob)
    return empty_swap


def test_exchange(swap, charlie, meta_token):
    amount = 1000 * 10**18
    mint_for_testing(charlie, amount, meta_token, False)
    meta_token.approve(swap.address, 2**256 - 1, sender=charlie)
    swap.exchange(0, 1, amount, 0, sender=charlie)


def test_exchange_underlying(swap, charlie, meta_token, base_pool_tokens):

    base_pool_index = 0
    amount = 1000 * 10**18
    mint_for_testing(charlie, amount, meta_token, False)
    mint_for_testing(charlie, amount, base_pool_tokens[base_pool_index], False)

    swap.exchange_underlying(1, 0)
