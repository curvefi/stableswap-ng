import pytest

INITIAL_AMOUNT = 1_000_000


@pytest.fixture(scope="module")
def initial_balance() -> int:
    return INITIAL_AMOUNT * 10**18


@pytest.fixture(scope="module")
def initial_amounts(underlying_decimals: list[int], pool_type) -> list[int]:
    _decimals = underlying_decimals.copy()
    if pool_type == 1:
        _decimals.pop(1)
    return [INITIAL_AMOUNT * 10**precision for precision in _decimals]


@pytest.fixture(scope="module")
def deposit_amounts(initial_amounts: list[int]) -> list[int]:
    return [ia // 2 for ia in initial_amounts]


@pytest.fixture(scope="module")
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"
