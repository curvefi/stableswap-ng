import pytest


@pytest.fixture(scope="module")
def coins(swap_plain):
    return [swap_plain.coins(0), swap_plain.coins(1)]


@pytest.fixture(scope="module")
def decimals(coins):
    return [coins[0].decimals(), coins[1].decimals()]
