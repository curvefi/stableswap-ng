import pytest

INITIAL_AMOUNT = 1_000_000


@pytest.fixture(scope="function")
def initial_balance() -> int:
    return INITIAL_AMOUNT * 10**18


@pytest.fixture(scope="function")
def initial_amounts(pool_type, decimals, meta_decimals) -> list[int]:
    return (
        [INITIAL_AMOUNT * 10**precision for precision in decimals]
        if pool_type == 0
        else [INITIAL_AMOUNT * 10**meta_decimals, INITIAL_AMOUNT * 10**18]
    )


@pytest.fixture(scope="function")
def deposit_amounts(initial_amounts: list[int]) -> list[int]:
    return [ia // 2 for ia in initial_amounts]


@pytest.fixture(scope="function")
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"
