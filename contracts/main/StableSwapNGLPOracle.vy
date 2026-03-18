# pragma version 0.4.3
# pragma optimize gas
"""
@title StableSwapNGLPOracle
@author Curve.Fi
@license MIT
@notice LP oracle for StableSwap-NG (n=2) reusing lp_oracle_bisection math.
"""

from curve_std.stableswap import lp_oracle_2


interface IStableSwapNG:
    def A_precise() -> uint256: view
    def get_virtual_price() -> uint256: view
    def price_oracle(i: uint256) -> uint256: view


PRECISION: constant(uint256) = 10**18
N_COINS: constant(uint256) = 2
POOL_A_PRECISION: constant(uint256) = 100


@internal
@view
def _sanity_check(pool: IStableSwapNG):
    # Basic sanity checks for required pool methods.
    assert staticcall pool.get_virtual_price() > 0
    assert staticcall pool.price_oracle(0) > 0
    assert staticcall pool.A_precise() > POOL_A_PRECISION, "Bad A value"
    success: bool = False
    response: Bytes[32] = b""
    success, response = raw_call(
        pool.address,
        abi_encode(convert(2, uint256), method_id=method_id("coins(uint256)")),
        max_outsize=32,
        revert_on_failure=False,
        is_static_call=True,
    )
    assert not success, "Supports only 2-coin pool"

@view
@external
def sanity_check(_pool: IStableSwapNG) -> bool:
    """
    @notice Validates core pool parameters required by this oracle.
    @param _pool Address of the StableSwapNG pool.
    @return bool True if all sanity checks pass, otherwise reverts.
    """
    self._sanity_check(_pool)
    return True


@internal
@view
def _scaled_A_raw(pool: IStableSwapNG) -> uint256:
    # Pool stores A as: A_true * N_COINS**(N_COINS-1) * 100.
    # Solver expects: A_true * solver.A_PRECISION.
    A_pool: uint256 = staticcall pool.A_precise()
    return unsafe_div(
        A_pool * lp_oracle_2.A_PRECISION,
        N_COINS**(N_COINS-1) * POOL_A_PRECISION
    )

@internal
@view
def _portfolio_value(pool: IStableSwapNG, i: uint256=0) -> uint256:
    assert i < N_COINS

    p_oracle: uint256 = staticcall pool.price_oracle(0)
    x_py: uint256 = lp_oracle_2._portfolio_value(self._scaled_A_raw(pool), p_oracle)

    if i == 1:
        return x_py * PRECISION // p_oracle
    return x_py

@internal
@view
def _lp_price(pool: IStableSwapNG, i: uint256=0) -> uint256:
    return unsafe_div(self._portfolio_value(pool, i) * staticcall pool.get_virtual_price(), PRECISION)


@view
@external
def portfolio_value(_pool: IStableSwapNG, _i: uint256=0) -> uint256:
    """
    @notice Returns the pool portfolio value in the selected coin numeraire.
    @param _pool Address of the StableSwapNG pool.
    @param _i Coin index used as the numeraire, where 0 or 1 are supported.
    @return uint256 Portfolio value scaled to 1e18 in coin `_i` units.
    """
    return self._portfolio_value(_pool, _i)


@external
@view
def lp_price(_pool: IStableSwapNG, _i: uint256=0) -> uint256:
    """
    @notice Returns LP token price in the selected coin numeraire.
    @param _pool Address of the StableSwapNG pool.
    @param _i Coin index used as the numeraire, where 0 or 1 are supported.
    @return uint256 LP price scaled to 1e18 in coin `_i` units.
    """
    return self._lp_price(_pool, _i)
