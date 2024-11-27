import pytest

INITIAL_AMOUNT = 3_000_000


@pytest.fixture(scope="session")
def initial_balance() -> int:
    return INITIAL_AMOUNT * 10**18


@pytest.fixture()
def meta_initial_amounts(meta_decimals) -> list[int]:
    return [INITIAL_AMOUNT * 10**meta_decimals, INITIAL_AMOUNT * 10**18]


@pytest.fixture()
def basic_initial_amounts(decimals) -> list[int]:
    return [INITIAL_AMOUNT * 10**precision for precision in decimals]


@pytest.fixture()
def initial_amounts(pool_type, basic_initial_amounts, meta_initial_amounts) -> list[int]:
    return basic_initial_amounts if pool_type == 0 else meta_initial_amounts


@pytest.fixture()
def deposit_basic_amounts(initial_amounts: list[int], pool_token_types, pool_tokens) -> list[int]:
    return [
        (
            initial_amounts[i] * 10**18 // pool_token.exchangeRate() // 2
            if pool_token_type == 1
            else initial_amounts[i] // 2
        )
        for i, (pool_token_type, pool_token) in enumerate(zip(pool_token_types, pool_tokens))
    ]


@pytest.fixture()
def deposit_meta_amounts(
    meta_initial_amounts: list[int], metapool_token_type, pool_tokens, underlying_tokens
) -> list[int]:
    return [
        (
            meta_initial_amounts[0] // 2
            if metapool_token_type != 1
            else meta_initial_amounts[0] * 10**18 // underlying_tokens[0].exchangeRate() // 2
        ),
        meta_initial_amounts[1] // 2,
    ]


@pytest.fixture()
def deposit_amounts(deposit_basic_amounts, deposit_meta_amounts, pool_type) -> list[int]:
    # This (almost) adds liquidity in balance for oracle tokens
    if pool_type == 0:
        return deposit_basic_amounts
    return deposit_meta_amounts


@pytest.fixture(scope="session")
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"
