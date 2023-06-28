import pytest

INITIAL_AMOUNT = 1_000_000


@pytest.fixture(scope="module")
def initial_amounts(decimals: list[int]) -> list[int]:
    return [INITIAL_AMOUNT * 10**precision for precision in decimals]


@pytest.fixture(scope="module")
def deposit_amounts(initial_amounts: list[int]) -> list[int]:
    return [ia // 2 for ia in initial_amounts]


@pytest.fixture(scope="module")
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"
