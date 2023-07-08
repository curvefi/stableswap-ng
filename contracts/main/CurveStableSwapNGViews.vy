# @version 0.3.9
"""
@title CurveStableSwap2NG
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2020-2023 - all rights reserved
@notice Auxiliary contract for Stableswap-NG containing utility methods for
        integrators
"""

interface StableSwapNG:
    def N_COINS() -> uint256: view
    def BASE_POOL() -> address: view
    def BASE_N_COINS() -> uint256: view
    def stored_rates(i: uint256) -> uint256: view
    def balances(i: uint256) -> uint256: view
    def fee() -> uint256: view
    def get_dy(i: int128, j: int128, dx: uint256) -> uint256: view
    def A() -> uint256: view
    def calc_withdraw_one_coin(_token_amount: uint256, i: int128) -> uint256: view
    def totalSupply() -> uint256: view
    def calc_token_amount(amounts: DynArray[uint256, MAX_COINS], deposit: bool) -> uint256: view

interface StableSwap2:
    def calc_token_amount(amounts: uint256[2], deposit: bool) -> uint256: view

interface StableSwap3:
    def calc_token_amount(amounts: uint256[3], deposit: bool) -> uint256: view

# TODO: Add up until 7 (a basepool can have maximally 7 if 8 is MAX_COINS. the other 1 is the non base pool token.)


A_PRECISION: constant(uint256) = 100
MAX_COINS: constant(uint256) = 8
PRECISION: constant(uint256) = 10 ** 18
FEE_DENOMINATOR: constant(uint256) = 10 ** 10


# ------------------------------ Public Getters ------------------------------


@view
@external
def get_dx(i: int128, j: int128, dy: uint256, pool: address) -> uint256:
    """
    @notice Calculate the current input dx given output dy
    @dev Index values can be found via the `coins` public getter method
    @param i Index value for the coin to send
    @param j Index valie of the coin to recieve
    @param dy Amount of `j` being received after exchange
    @return Amount of `i` predicted
    """
    N_COINS: uint256 = StableSwapNG(pool).N_COINS()

    rates: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    balances: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    xp: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    rates, balances, xp = self._get_rates_balances_xp(pool, N_COINS)

    y: uint256 = xp[j] - (dy * rates[j] / PRECISION + 1) * FEE_DENOMINATOR / (FEE_DENOMINATOR - StableSwapNG(pool).fee())
    x: uint256 = self.get_y(j, i, y, xp, 0, 0, N_COINS)
    return (x - xp[i]) * PRECISION / rates[i]


@view
@external
def get_dy(i: int128, j: int128, dx: uint256, pool: address) -> uint256:
    """
    @notice Calculate the current output dy given input dx
    @dev Index values can be found via the `coins` public getter method
    @param i Index value for the coin to send
    @param j Index valie of the coin to recieve
    @param dx Amount of `i` being exchanged
    @return Amount of `j` predicted
    """
    N_COINS: uint256 = StableSwapNG(pool).N_COINS()

    rates: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    balances: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    xp: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    rates, balances, xp = self._get_rates_balances_xp(pool, N_COINS)


    x: uint256 = xp[i] + (dx * rates[i] / PRECISION)
    y: uint256 = self.get_y(i, j, x, xp, 0, 0, N_COINS)
    dy: uint256 = xp[j] - y - 1
    fee: uint256 = StableSwapNG(pool).fee() * dy / FEE_DENOMINATOR
    return (dy - fee) * PRECISION / rates[j]


@view
@external
def get_dx_underlying(
    i: int128,
    j: int128,
    dx: uint256,
    pool: address,
) -> uint256:
    # TODO: Add get_dx_underlying
    return 0


@view
@external
def get_dy_underlying(
    i: int128,
    j: int128,
    dx: uint256,
    pool: address,
) -> uint256:
    """
    @notice Calculate the current output dy given input dx on underlying
    @dev Index values can be found via the `coins` public getter method
    @param i Index value for the coin to send
    @param j Index valie of the coin to recieve
    @param dx Amount of `i` being exchanged
    @return Amount of `j` predicted
    """

    N_COINS: uint256 = StableSwapNG(pool).N_COINS()
    MAX_COIN: int128 = convert(N_COINS, int128) - 1
    BASE_POOL: address = StableSwapNG(pool).BASE_POOL()

    rates: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    balances: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    xp: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    rates, balances, xp = self._get_rates_balances_xp(pool, N_COINS)

    x: uint256 = 0
    base_i: int128 = 0
    base_j: int128 = 0
    meta_i: int128 = 0
    meta_j: int128 = 0

    if i != 0:
        base_i = i - MAX_COIN
        meta_i = 1
    if j != 0:
        base_j = j - MAX_COIN
        meta_j = 1

    if i == 0:
        x = xp[i] + dx * (rates[0] / 10**18)
    else:
        if j == 0:
            # i is from BasePool
            base_n_coins: uint256 = StableSwapNG(pool).BASE_N_COINS()
            x = self._base_calc_token_amounts_deposit(
                dx, base_i, rates[1], base_n_coins, BASE_POOL
            )
            # Accounting for deposit/withdraw fees approximately
            x -= x * StableSwapNG(BASE_POOL).fee() / (2 * FEE_DENOMINATOR)
            # Adding number of pool tokens
            x += xp[MAX_COIN]
        else:
            # If both are from the base pool
            return StableSwapNG(BASE_POOL).get_dy(base_i, base_j, dx)

    # This pool is involved only when in-pool assets are used
    amp: uint256 = StableSwapNG(pool).A() * A_PRECISION
    D: uint256 = self.get_D(xp, amp, N_COINS)
    y: uint256 = self.get_y(meta_i, meta_j, x, xp, amp, D, N_COINS)
    dy: uint256 = xp[meta_j] - y - 1
    dy = (dy - StableSwapNG(pool).fee() * dy / FEE_DENOMINATOR)

    # If output is going via the metapool
    if j == 0:
        dy /= (rates[0] / 10**18)
    else:
        # j is from BasePool
        # The fee is already accounted for
        dy = StableSwapNG(BASE_POOL).calc_withdraw_one_coin(dy * PRECISION / rates[1], base_j)

    return dy


@view
@external
def calc_token_amount(
    _amounts: DynArray[uint256, MAX_COINS],
    _is_deposit: bool,
    pool: address
) -> uint256:
    """
    @notice Calculate addition or reduction in token supply from a deposit or withdrawal
    @param _amounts Amount of each coin being deposited
    @param _is_deposit set True for deposits, False for withdrawals
    @return Expected amount of LP tokens received
    """
    amp: uint256 = StableSwapNG(pool).A() * A_PRECISION
    N_COINS: uint256 = StableSwapNG(pool).N_COINS()

    rates: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    old_balances: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    xp: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    rates, old_balances, xp = self._get_rates_balances_xp(pool, N_COINS)

    # Initial invariant
    D0: uint256 = self.get_D(xp, amp, N_COINS)

    total_supply: uint256 = StableSwapNG(pool).totalSupply()
    new_balances: DynArray[uint256, MAX_COINS] = old_balances
    for i in range(MAX_COINS):
        if i == N_COINS:
            break

        amount: uint256 = _amounts[i]
        if _is_deposit:
            new_balances[i] += amount
        else:
            new_balances[i] -= amount

    # Invariant after change
    for idx in range(MAX_COINS):
        if idx == N_COINS:
            break
        xp[idx] = rates[idx] * new_balances[idx] / PRECISION
    D1: uint256 = self.get_D(xp, amp, N_COINS)

    # We need to recalculate the invariant accounting for fees
    # to calculate fair user's share
    D2: uint256 = D1
    if total_supply > 0:

        # Only account for fees if we are not the first to deposit
        base_fee: uint256 = StableSwapNG(pool).fee() * N_COINS / (4 * (N_COINS - 1))
        for i in range(MAX_COINS):
            if i == N_COINS:
                break

            ideal_balance: uint256 = D1 * old_balances[i] / D0
            difference: uint256 = 0
            new_balance: uint256 = new_balances[i]
            if ideal_balance > new_balance:
                difference = ideal_balance - new_balance
            else:
                difference = new_balance - ideal_balance
            new_balances[i] -= base_fee * difference / FEE_DENOMINATOR

        for idx in range(MAX_COINS):
            if idx == N_COINS:
                break
            xp[idx] = rates[idx] * new_balances[idx] / PRECISION

        D2 = self.get_D(xp, amp, N_COINS)
    else:
        return D1  # Take the dust if there was any

    diff: uint256 = 0
    if _is_deposit:
        diff = D2 - D0
    else:
        diff = D0 - D2
    return diff * total_supply / D0


@view
@external
def calc_withdraw_one_coin(_burn_amount: uint256, i: int128, pool: address) -> uint256:
    # First, need to calculate
    # * Get current D
    # * Solve Eqn against y_i for D - _token_amount

    amp: uint256 = StableSwapNG(pool).A() * A_PRECISION
    N_COINS: uint256 = StableSwapNG(pool).N_COINS()

    rates: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    balances: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    xp: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    rates, balances, xp = self._get_rates_balances_xp(pool, N_COINS)

    D0: uint256 = self.get_D(xp, amp, N_COINS)

    total_supply: uint256 = StableSwapNG(pool).totalSupply()
    D1: uint256 = D0 - _burn_amount * D0 / total_supply
    new_y: uint256 = self.get_y_D(amp, i, xp, D1, N_COINS)

    base_fee: uint256 = StableSwapNG(pool).fee() * N_COINS / (4 * (N_COINS - 1))
    xp_reduced: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])

    for j in range(MAX_COINS):

        if j == N_COINS:
            break

        dx_expected: uint256 = 0
        xp_j: uint256 = xp[j]
        if convert(j, int128) == i:
            dx_expected = xp_j * D1 / D0 - new_y
        else:
            dx_expected = xp_j - xp_j * D1 / D0
        xp_reduced[j] = xp_j - base_fee * dx_expected / FEE_DENOMINATOR

    dy: uint256 = xp_reduced[i] - self.get_y_D(amp, i, xp_reduced, D1, N_COINS)
    dy_0: uint256 = (xp[i] - new_y) * PRECISION / rates[i]  # w/o fees
    dy = (dy - 1) * PRECISION / rates[i]  # Withdraw less to account for rounding errors

    return dy


# ----------------------------- Utility Methods ------------------------------


@internal
@view
def _base_calc_token_amounts_deposit(
    dx: uint256, base_i: int128, meta_vprice: uint256, base_n_coins: uint256, base_pool: address
) -> uint256:

    if base_n_coins == 2:

        base_inputs: uint256[2] = empty(uint256[2])
        base_inputs[base_i] = dx
        return StableSwap2(base_pool).calc_token_amount(base_inputs, True) * meta_vprice / PRECISION

    elif base_n_coins == 3:

        base_inputs: uint256[3] = empty(uint256[3])
        base_inputs[base_i] = dx
        return StableSwap3(base_pool).calc_token_amount(base_inputs, True) * meta_vprice / PRECISION

    else:

        raise "base_n_coins > 3 not supported yet."


@internal
@pure
def newton_y(b: uint256, c: uint256, D: uint256, _y: uint256) -> uint256:

    y_prev: uint256 = 0
    y: uint256 = _y

    for _i in range(255):
        y_prev = y
        y = (y*y + c) / (2 * y + b - D)
        # Equality with the precision of 1
        if y > y_prev:
            if y - y_prev <= 1:
                return y
        else:
            if y_prev - y <= 1:
                return y
    raise


@view
@internal
def get_y(
    i: int128,
    j: int128,
    x: uint256,
    xp: DynArray[uint256, MAX_COINS],
    _amp: uint256,
    _D: uint256,
    N_COINS: uint256
) -> uint256:
    """
    Calculate x[j] if one makes x[i] = x

    Done by solving quadratic equation iteratively.
    x_1**2 + x_1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    # x in the input is converted to the same price/precision

    assert i != j       # dev: same coin
    assert j >= 0       # dev: j below zero
    assert j < convert(N_COINS, int128)  # dev: j above N_COINS

    # should be unreachable, but good for safety
    assert i >= 0
    assert i < convert(N_COINS, int128)

    amp: uint256 = _amp
    D: uint256 = _D
    S_: uint256 = 0
    _x: uint256 = 0
    c: uint256 = D
    Ann: uint256 = amp * N_COINS

    for _i in range(MAX_COINS):

        if _i == N_COINS:
            break

        if  convert(_i, int128) == i:
            _x = x
        elif convert(_i, int128) != j:
            _x = xp[_i]
        else:
            continue
        S_ += _x
        c = c * D / (_x * N_COINS)

    c = c * D * A_PRECISION / (Ann * N_COINS)
    b: uint256 = S_ + D * A_PRECISION / Ann  # - D
    y: uint256 = D

    return self.newton_y(b, c, D, y)


@pure
@internal
def get_D(_xp: DynArray[uint256, MAX_COINS], _amp: uint256, N_COINS: uint256) -> uint256:
    """
    D invariant calculation in non-overflowing integer operations
    iteratively

    A * sum(x_i) * n**n + D = A * D * n**n + D**(n+1) / (n**n * prod(x_i))

    Converging solution:
    D[j+1] = (A * n**n * sum(x_i) - D[j]**(n+1) / (n**n prod(x_i))) / (A * n**n - 1)
    """
    S: uint256 = 0
    for i in range(MAX_COINS):
        if i == N_COINS:
            break
        S += _xp[i]

    if S == 0:
        return 0

    D: uint256 = S
    Ann: uint256 = _amp * N_COINS
    for i in range(255):
        D_P: uint256 = D * D / _xp[0] * D / _xp[1] / pow_mod256(N_COINS, N_COINS)
        Dprev: uint256 = D
        D = (Ann * S / A_PRECISION + D_P * N_COINS) * D / ((Ann - A_PRECISION) * D / A_PRECISION + (N_COINS + 1) * D_P)
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


@pure
@internal
def get_y_D(
    A: uint256,
    i: int128,
    xp: DynArray[uint256, MAX_COINS],
    D: uint256,
    N_COINS: uint256
) -> uint256:
    """
    Calculate x[i] if one reduces D from being calculated for xp to D

    Done by solving quadratic equation iteratively.
    x_1**2 + x_1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    # x in the input is converted to the same price/precision

    N_COINS_128: int128 = convert(N_COINS, int128)
    assert i >= 0  # dev: i below zero
    assert i < N_COINS_128  # dev: i above N_COINS

    S_: uint256 = 0
    _x: uint256 = 0
    y_prev: uint256 = 0
    c: uint256 = D
    Ann: uint256 = A * N_COINS

    for _i in range(MAX_COINS):

        if _i == N_COINS:
            break

        if _i != convert(i, uint256):
            _x = xp[_i]
        else:
            continue
        S_ += _x
        c = c * D / (_x * N_COINS)

    c = c * D * A_PRECISION / (Ann * N_COINS)
    b: uint256 = S_ + D * A_PRECISION / Ann
    y: uint256 = D

    return self.newton_y(b, c, D, y)


@view
@internal
def _get_rates_balances_xp(pool: address, N_COINS: uint256) -> (
    DynArray[uint256, MAX_COINS],
    DynArray[uint256, MAX_COINS],
    DynArray[uint256, MAX_COINS],
):

    rates: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    balances: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    rate: uint256 = 0

    # Get rates and balances:
    for idx in range(MAX_COINS):
        if idx == N_COINS:
            break
        rate = StableSwapNG(pool).stored_rates(idx)
        rates[idx] = StableSwapNG(pool).stored_rates(idx)
        balances[idx] = StableSwapNG(pool).balances(idx)

    xp: DynArray[uint256, MAX_COINS] = empty(DynArray[uint256, MAX_COINS])
    for idx in range(MAX_COINS):
        if idx == N_COINS:
            break
        xp[idx] = rates[idx] * balances[idx] / PRECISION

    return rates, balances, xp
