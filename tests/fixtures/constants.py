import pytest

INITIAL_AMOUNT = 1_000_000


@pytest.fixture(scope="module")
def initial_amounts(decimals: list[int]) -> list[int]:
    return [INITIAL_AMOUNT * 10**precision for precision in decimals]


@pytest.fixture(scope="module")
def initial_amounts_underlying(underlying_decimals: list[int]) -> list[int]:
    amts = [INITIAL_AMOUNT * 10**precision for precision in underlying_decimals]
    for i in range(1, len(underlying_decimals)):
        amts[i] //= len(underlying_decimals) - 1
    return amts


@pytest.fixture(scope="module")
def deposit_amounts(decimals: list[int]) -> list[int]:
    return [INITIAL_AMOUNT // 2 * 10**18 for _ in decimals]  # xp is always 18


@pytest.fixture(scope="module")
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"
