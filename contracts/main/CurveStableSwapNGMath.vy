# pragma version 0.3.10
# pragma optimize gas
# pragma evm-version shanghai
"""
@title CurveStableSwapNGMath
@author Curve.Fi
@license Copyright (c) Curve.Fi, 2020-2023 - all rights reserved
@notice Math for StableSwapMetaNG implementation
"""

MAX_COINS: constant(uint256) = 8
MAX_COINS_128: constant(int128) = 8
A_PRECISION: constant(uint256) = 100

interface ERC4626:
    def convertToAssets(shares: uint256) -> uint256: view

# shift(2**32 - 1, 224)
ORACLE_BIT_MASK: constant(uint256) = (2**32 - 1) * 256**28


@external
@pure
def get_y(
    i: int128,
    j: int128,
    x: uint256,
    xp: DynArray[uint256, MAX_COINS],
    _amp: uint256,
    _D: uint256,
    _n_coins: uint256
) -> uint256:
    """
    Calculate x[j] if one makes x[i] = x

    Done by solving quadratic equation iteratively.
    x_1**2 + x_1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    # x in the input is converted to the same price/precision

    n_coins_128: int128 = convert(_n_coins, int128)

    assert i != j       # dev: same coin
    assert j >= 0       # dev: j below zero
    assert j < n_coins_128  # dev: j above N_COINS

    # should be unreachable, but good for safety
    assert i >= 0
    assert i < n_coins_128

    amp: uint256 = _amp
    D: uint256 = _D
    S_: uint256 = 0
    _x: uint256 = 0
    y_prev: uint256 = 0
    c: uint256 = D
    Ann: uint256 = amp * _n_coins

    for _i in range(MAX_COINS_128):

        if _i == n_coins_128:
            break

        if _i == i:
            _x = x
        elif _i != j:
            _x = xp[_i]
        else:
            continue

        S_ += _x
        c = c * D / (_x * _n_coins)

    c = c * D * A_PRECISION / (Ann * _n_coins)
    b: uint256 = S_ + D * A_PRECISION / Ann  # - D
    y: uint256 = D

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


@external
@pure
def get_D(
    _xp: DynArray[uint256, MAX_COINS],
    _amp: uint256,
    _n_coins: uint256
) -> uint256:
    """
    D invariant calculation in non-overflowing integer operations
    iteratively

    A * sum(x_i) * n**n + D = A * D * n**n + D**(n+1) / (n**n * prod(x_i))

    Converging solution:
    D[j+1] = (A * n**n * sum(x_i) - D[j]**(n+1) / (n**n prod(x_i))) / (A * n**n - 1)
    """
    S: uint256 = 0
    for x in _xp:
        S += x
    if S == 0:
        return 0

    D: uint256 = S
    Ann: uint256 = _amp * _n_coins

    for i in range(255):

        D_P: uint256 = D
        for x in _xp:
            D_P = D_P * D / x  # If division by 0, this will be borked: only withdrawal will work. And that is good
        D_P /= pow_mod256(_n_coins, _n_coins)
        Dprev: uint256 = D

        # (Ann * S / A_PRECISION + D_P * _n_coins) * D / ((Ann - A_PRECISION) * D / A_PRECISION + (_n_coins + 1) * D_P)
        D = (
            (unsafe_div(Ann * S, A_PRECISION) + D_P * _n_coins) *
            D / (
                unsafe_div((Ann - A_PRECISION) * D, A_PRECISION) +
                unsafe_add(_n_coins, 1) * D_P
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


@external
@pure
def get_y_D(
    A: uint256,
    i: int128,
    xp: DynArray[uint256, MAX_COINS],
    D: uint256,
    _n_coins: uint256
) -> uint256:
    """
    Calculate x[i] if one reduces D from being calculated for xp to D

    Done by solving quadratic equation iteratively.
    x_1**2 + x_1 * (sum' - (A*n**n - 1) * D / (A * n**n)) = D ** (n + 1) / (n ** (2 * n) * prod' * A)
    x_1**2 + b*x_1 = c

    x_1 = (x_1**2 + c) / (2*x_1 + b)
    """
    # x in the input is converted to the same price/precision

    n_coins_128: int128 = convert(_n_coins, int128)

    assert i >= 0  # dev: i below zero
    assert i < n_coins_128  # dev: i above N_COINS

    S_: uint256 = 0
    _x: uint256 = 0
    y_prev: uint256 = 0
    c: uint256 = D
    Ann: uint256 = A * _n_coins

    for _i in range(MAX_COINS_128):

        if _i == n_coins_128:
            break

        if _i != i:
            _x = xp[_i]
        else:
            continue
        S_ += _x
        c = c * D / (_x * _n_coins)

    c = c * D * A_PRECISION / (Ann * _n_coins)
    b: uint256 = S_ + D * A_PRECISION / Ann
    y: uint256 = D

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


@external
@pure
def exp(x: int256) -> uint256:

    """
    @dev Calculates the natural exponential function of a signed integer with
         a precision of 1e18.
    @notice Note that this function consumes about 810 gas units. The implementation
            is inspired by Remco Bloemen's implementation under the MIT license here:
            https://xn--2-umb.com/22/exp-ln.
    @dev This implementation is derived from Snekmate, which is authored
         by pcaversaccio (Snekmate), distributed under the AGPL-3.0 license.
         https://github.com/pcaversaccio/snekmate
    @param x The 32-byte variable.
    @return int256 The 32-byte calculation result.
    """
    value: int256 = x

    # If the result is `< 0.5`, we return zero. This happens when we have the following:
    # "x <= floor(log(0.5e18) * 1e18) ~ -42e18".
    if (x <= -41446531673892822313):
        return empty(uint256)

    # When the result is "> (2 ** 255 - 1) / 1e18" we cannot represent it as a signed integer.
    # This happens when "x >= floor(log((2 ** 255 - 1) / 1e18) * 1e18) ~ 135".
    assert x < 135305999368893231589, "wad_exp overflow"

    # `x` is now in the range "(-42, 136) * 1e18". Convert to "(-42, 136) * 2 ** 96" for higher
    # intermediate precision and a binary base. This base conversion is a multiplication with
    # "1e18 / 2 ** 96 = 5 ** 18 / 2 ** 78".
    value = unsafe_div(x << 78, 5 ** 18)

    # Reduce the range of `x` to "(-½ ln 2, ½ ln 2) * 2 ** 96" by factoring out powers of two
    # so that "exp(x) = exp(x') * 2 ** k", where `k` is a signer integer. Solving this gives
    # "k = round(x / log(2))" and "x' = x - k * log(2)". Thus, `k` is in the range "[-61, 195]".
    k: int256 = unsafe_add(unsafe_div(value << 96, 54916777467707473351141471128), 2 ** 95) >> 96
    value = unsafe_sub(value, unsafe_mul(k, 54916777467707473351141471128))

    # Evaluate using a "(6, 7)"-term rational approximation. Since `p` is monic,
    # we will multiply by a scaling factor later.
    y: int256 = unsafe_add(unsafe_mul(unsafe_add(value, 1346386616545796478920950773328), value) >> 96, 57155421227552351082224309758442)
    p: int256 = unsafe_add(unsafe_mul(unsafe_add(unsafe_mul(unsafe_sub(unsafe_add(y, value), 94201549194550492254356042504812), y) >> 96,\
                           28719021644029726153956944680412240), value), 4385272521454847904659076985693276 << 96)

    # We leave `p` in the "2 ** 192" base so that we do not have to scale it up
    # again for the division.
    q: int256 = unsafe_add(unsafe_mul(unsafe_sub(value, 2855989394907223263936484059900), value) >> 96, 50020603652535783019961831881945)
    q = unsafe_sub(unsafe_mul(q, value) >> 96, 533845033583426703283633433725380)
    q = unsafe_add(unsafe_mul(q, value) >> 96, 3604857256930695427073651918091429)
    q = unsafe_sub(unsafe_mul(q, value) >> 96, 14423608567350463180887372962807573)
    q = unsafe_add(unsafe_mul(q, value) >> 96, 26449188498355588339934803723976023)

    # The polynomial `q` has no zeros in the range because all its roots are complex.
    # No scaling is required, as `p` is already "2 ** 96" too large. Also,
    # `r` is in the range "(0.09, 0.25) * 2**96" after the division.
    r: int256 = unsafe_div(p, q)

    # To finalise the calculation, we have to multiply `r` by:
    #   - the scale factor "s = ~6.031367120",
    #   - the factor "2 ** k" from the range reduction, and
    #   - the factor "1e18 / 2 ** 96" for the base conversion.
    # We do this all at once, with an intermediate result in "2**213" base,
    # so that the final right shift always gives a positive value.

    # Note that to circumvent Vyper's safecast feature for the potentially
    # negative parameter value `r`, we first convert `r` to `bytes32` and
    # subsequently to `uint256`. Remember that the EVM default behaviour is
    # to use two's complement representation to handle signed integers.
    return unsafe_mul(convert(convert(r, bytes32), uint256), 3822833074963236453042738258902158003155416615667) >> convert(unsafe_sub(195, k), uint256)


@external
@pure
def bound_rates(
    _rates: DynArray[uint256, MAX_COINS],
    _last: DynArray[uint256, MAX_COINS],
    _bump: uint256,
    _limit: uint256,
) -> (DynArray[uint256, MAX_COINS], bool):
    """
    @notice Bound a pool's rates against the ones it last accepted.
    @dev No coin moves more than _bump, and no two coins move apart by more than
         _bump, a coin whose rate cannot move counting as unmoved: bounded one at
         a time, two rates pushed opposite ways would pay out as one step of twice
         _bump. A coin whose _last is 0 is unseeded and passes through. The second
         value is whether any reading is further than _limit from its anchor; a
         _limit of 0 skips that test. Both are FEE_DENOMINATOR (1e10) scaled.
    @param _rates Rates as the pool's sources report them now
    @param _last The rates the pool last accepted
    @param _bump The furthest one update may move a rate
    @param _limit The furthest a reading may sit from its anchor before it halts the pool
    @return The bounded rates, and whether they halt the pool
    """
    rates: DynArray[uint256, MAX_COINS] = _rates
    n: uint256 = len(_rates)
    b: int256 = convert(_bump, int256)
    fd: int256 = 10**10
    raw: int256[MAX_COINS] = empty(int256[MAX_COINS])
    hi: int256 = 0
    lo: int256 = 0
    halt: bool = False
    for i in range(n, bound=MAX_COINS):
        if _last[i] != 0:
            u: int256 = convert(_rates[i] * 10**10 / _last[i], int256) - fd
            if _limit != 0 and abs(u) > convert(_limit, int256):
                halt = True
            hi = max(hi, min(u, b))
            lo = min(lo, max(u, -b))
            raw[i] = u
    # every move must fit one window of width _bump that also holds 0, the unmoved coins
    c: int256 = 0
    w: int256 = b
    if hi - lo > b:
        w = b / 2
        c = min(max((hi + lo) / 2, -w), w)
    for i in range(n, bound=MAX_COINS):
        m: int256 = min(max(raw[i], c - w), c + w)
        if m != raw[i]:
            rates[i] = convert(convert(_last[i], int256) * (fd + m) / fd, uint256)
    return rates, halt


@external
@view
def rate_now(
    _coin: address,
    _asset_type: uint8,
    _rate_oracle: uint256,
    _rate_multiplier: uint256,
    _call_amount: uint256,
    _scale_factor: uint256,
) -> uint256:
    """
    @notice One coin's rate as its source reports it now, for a pool seeding its bound at deploy.
    @dev The pool's rate fetch for one coin, kept here so the pools stay under EIP-170.
         Fails closed: a source that reverts, or answers with anything but 32 bytes, reverts.
    @param _coin The coin; read for an ERC4626 vault (asset type 3)
    @param _asset_type The coin's asset type
    @param _rate_oracle [bytes4 method_id][bytes8 <empty>][bytes20 oracle], for asset type 1
    @param _rate_multiplier 10 ** (36 - the coin's decimals)
    @param _call_amount 10 ** the vault's decimals, for asset type 3
    @param _scale_factor 10 ** (18 - the vault asset's decimals), for asset type 3
    @return The rate, 1e18 precision, as the pool would compute it
    """
    if _asset_type == 1 and _rate_oracle != 0:
        response: Bytes[32] = raw_call(
            convert(_rate_oracle % 2**160, address),
            _abi_encode(_rate_oracle & ORACLE_BIT_MASK),
            max_outsize=32,
            is_static_call=True,
        )
        assert len(response) == 32
        return unsafe_div(_rate_multiplier * convert(response, uint256), 10**18)
    if _asset_type == 3:
        return unsafe_div(_rate_multiplier * ERC4626(_coin).convertToAssets(_call_amount) * _scale_factor, 10**18)
    return _rate_multiplier
