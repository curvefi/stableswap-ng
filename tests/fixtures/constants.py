import pytest

INITIAL_AMOUNT = 3_000_000


@pytest.fixture(scope="module")
def initial_balance() -> int:
    return INITIAL_AMOUNT * 10**18


@pytest.fixture(scope="module")
def initial_amounts(pool_type, decimals, meta_decimals) -> list[int]:
    return (
        [INITIAL_AMOUNT * 10**precision for precision in decimals]
        if pool_type == 0
        else [INITIAL_AMOUNT * 10**meta_decimals, INITIAL_AMOUNT * 10**18]
    )


@pytest.fixture(scope="module")
def deposit_amounts(
    initial_amounts: list[int], pool_type, pool_token_types, metapool_token_type, pool_tokens, underlying_tokens
) -> list[int]:
    amounts = []

    # This (almost) adds liquidity in balance for oracle tokens
    if pool_type == 0:
        i = 0
        for ptt, pt in zip(pool_token_types, pool_tokens):
            if ptt != 1:
                amounts.append(initial_amounts[i] // 2)
            else:
                amounts.append(initial_amounts[i] * 10**18 // pt.exchangeRate() // 2)
            i += 1
    else:
        if metapool_token_type != 1:
            amounts.append(initial_amounts[0] // 2)
        else:
            amounts.append(initial_amounts[0] * 10**18 // underlying_tokens[0].exchangeRate() // 2)

        amounts.append(initial_amounts[1] // 2)

    return amounts


@pytest.fixture(scope="module")
def zero_address() -> str:
    return "0x0000000000000000000000000000000000000000"
