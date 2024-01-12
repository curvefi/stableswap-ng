import boa
import pytest


@pytest.fixture(scope="module")
def new_math():

    return boa.loads(
        """
A_PRECISION: constant(uint256) = 100
N_COINS: constant(uint256) = 2
MAX_COINS: constant(uint256) = 8

@pure
@external
def get_D(_xp: DynArray[uint256, MAX_COINS], _amp: uint256) -> uint256:

    S: uint256 = 0
    for x in _xp:
        S += x
    if S == 0:
        return 0

    D: uint256 = S
    Ann: uint256 = _amp * N_COINS

    for i in range(255):

        D_P: uint256 = D
        for x in _xp:
            D_P = D_P * D / x
        D_P /= pow_mod256(N_COINS, N_COINS)
        Dprev: uint256 = D

        # (Ann * S / A_PRECISION + D_P * N_COINS) * D / ((Ann - A_PRECISION) * D / A_PRECISION + (N_COINS + 1) * D_P)
        D = (
            (unsafe_div(Ann * S, A_PRECISION) + D_P * N_COINS) * D
            /
            (
                unsafe_div((Ann - A_PRECISION) * D, A_PRECISION) +
                unsafe_add(N_COINS, 1) * D_P
            )
        )

        # Equality with the precision of 1
        if D > Dprev:
            if D - Dprev <= 1:
                return D
        else:
            if Dprev - D <= 1:
                return D
    # convergence typically occurs in 4 rounds or less, this should be unreachable!
    # if it does happen the pool is borked and LPs can withdraw via `remove_liquidity`
    raise
"""
    )


def test_convergence(new_math):
    assert new_math.get_D([10**23, 10**18], 1000) == 9010395375710532394006
