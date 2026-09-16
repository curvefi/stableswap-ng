"""The rate a trade pays must be fixed before the trade was visible.

Without the freeze, `_exchange` reads `_stored_rates()` inline, so a taker is priced
at whatever the oracle returns at the moment their transaction lands. Anyone able to
move that oracle - and for an asset-type-1 coin it is an arbitrary address chosen at
deploy time - could watch an order arrive and re-price it before it settled. Nothing
exotic was required: no limit exceeded, nothing front-run, no block reordered. The
operator changed a number they were entitled to change, at a moment of their
choosing, and collected the taker's slippage tolerance.

These pass now. The pool accepts a rate once per block and will not move it again
inside that block, so a quote and its fill agree; and across blocks a rate may move
by at most `max_rate_bump`, which is `2 * fee` in a two-coin pool - the largest step that
cannot be bracketed at a profit, since a round trip pays the fee twice. Each test
below is therefore a regression guard: if any of them goes red, the pool has started
pricing trades on a number that can change after the taker committed to it.

The last two check the constructor rather than the rate path. They belong here
because the same fourteen Arbitrum pools that motivated the freeze also carried
`A = 100000` and `offpeg_fee_multiplier = 0` - a flat invariant with the off-peg
brake disabled, which is what made an oracle move worth so much.

Constructed rather than forked because the live population is gone: those fourteen
pools were deployed already bricked and hold no value. The mechanism was in the
implementation, not in those pools.
"""

import boa
import pytest

from tests.fixtures.pools import OFFPEG_FEE_MULTIPLIER, ORACLE_METHOD_ID
from tests.utils.tokens import mint_for_testing

pytestmark = pytest.mark.usefixtures("initial_setup")

# What an aggregator would accept, in basis points. Routers quote a block or more
# ahead, so this is the room a taker has to leave for honest movement.
TOLERANCE_BPS = 50


def _oracle_coin(pool_tokens):
    """Index of a coin priced by an external oracle, or skip."""
    for i, token in enumerate(pool_tokens):
        if token.asset_type() == 1:
            return i
    pytest.skip("no oracle-backed coin in this pool")


@pytest.mark.only_oracle_tokens
def test_quote_survives_an_operator_reprice(bob, swap, pool_tokens, decimals):
    """A quote must still hold when the trade lands.

    The taker reads `get_dy`, signs for it with a tolerance, and the operator moves
    the oracle before it executes. What the taker loses should be bounded by the
    fee, not by whatever tolerance they happened to set.
    """
    receiving = _oracle_coin(pool_tokens)
    sending = 1 - receiving

    amount = 1_000 * 10 ** decimals[sending]
    mint_for_testing(bob, amount, pool_tokens[sending])

    quoted = swap.get_dy(sending, receiving, amount)
    min_dy = quoted * (10_000 - TOLERANCE_BPS) // 10_000

    # The operator raises the rate of the coin the taker is buying, so each unit
    # counts for more inside the invariant and fewer units come back out. The move
    # is sized to sit just inside the taker's tolerance.
    oracle_token = pool_tokens[receiving]
    rate = oracle_token.exchange_rate()
    oracle_token.set_exchange_rate(rate * (10_000 + TOLERANCE_BPS - 1) // 10_000)

    filled = swap.exchange(sending, receiving, amount, min_dy, sender=bob)

    lost = (quoted - filled) / quoted
    bound = 2 * swap.fee() / 10**10
    assert lost <= bound, (
        f"operator took {lost * 1e4:.2f} bp of the trade by repricing between quote "
        f"and fill; only {bound * 1e4:.2f} bp (2 * fee) is explainable"
    )


@pytest.mark.only_oracle_tokens
def test_min_dy_is_a_safety_bound_not_a_price(bob, swap, pool_tokens, decimals):
    """A tighter tolerance must not simply mean a smaller loss.

    If what the taker loses tracks whatever tolerance they set, then `_min_dy` has
    stopped being protection and become the operator's price. Quoting the same trade
    at two tolerances should not move the fill.
    """
    receiving = _oracle_coin(pool_tokens)
    sending = 1 - receiving
    amount = 1_000 * 10 ** decimals[sending]

    fills = {}
    for tolerance in (10, 100):
        with boa.env.anchor():
            mint_for_testing(bob, amount, pool_tokens[sending])
            quoted = swap.get_dy(sending, receiving, amount)
            min_dy = quoted * (10_000 - tolerance) // 10_000

            oracle_token = pool_tokens[receiving]
            rate = oracle_token.exchange_rate()
            oracle_token.set_exchange_rate(rate * (10_000 + tolerance - 1) // 10_000)

            fills[tolerance] = swap.exchange(sending, receiving, amount, min_dy, sender=bob)

    spread = abs(fills[10] - fills[100]) / fills[10]
    assert spread <= 2 * swap.fee() / 10**10, (
        f"the fill moved {spread * 1e4:.2f} bp purely because the taker's tolerance "
        f"changed: 10 bp gave {fills[10]}, 100 bp gave {fills[100]}"
    )


@pytest.mark.only_oracle_tokens
def test_reprice_within_one_block_is_bounded(bob, swap, pool_tokens, decimals):
    """Two trades in one block must not price differently by more than the fee.

    Nothing rate-side should be able to change inside a block. Here the operator
    moves the oracle between two identical trades in the same block, and the second
    taker pays for it.
    """
    receiving = _oracle_coin(pool_tokens)
    sending = 1 - receiving
    amount = 1_000 * 10 ** decimals[sending]

    mint_for_testing(bob, amount * 2, pool_tokens[sending])
    first = swap.exchange(sending, receiving, amount, 0, sender=bob)

    oracle_token = pool_tokens[receiving]
    oracle_token.set_exchange_rate(oracle_token.exchange_rate() * 10_050 // 10_000)

    second = swap.exchange(sending, receiving, amount, 0, sender=bob)

    drift = abs(first - second) / first
    bound = 2 * swap.fee() / 10**10
    assert drift <= bound, (
        f"two identical trades in one block differed by {drift * 1e4:.2f} bp "
        f"after an oracle move; {bound * 1e4:.2f} bp is explainable"
    )


@pytest.mark.only_oracle_tokens
def test_factory_rejects_amplification_above_max_a(
    deployer, factory, pool_tokens, zero_address, set_pool_implementations
):
    """A must be bounded when the pool is built, not only when it is ramped.

    `ramp_A` asserts `_future_A < MAX_A`, but the constructor takes `_A` straight
    into `unsafe_mul(_A, A_PRECISION)` with no check, and the factory does not
    validate it either. A pool can therefore be deployed far above MAX_A and then
    simply never ramped.

    It matters because a large enough A flattens the invariant towards constant-sum:
    the pool quotes one price with no curve resistance until a reserve runs out. Put
    that beside an oracle the deployer controls and `offpeg_fee_multiplier = 0` and
    every brake is off at once. Live pools on Base read A = 1e18 and 1e12 against a
    MAX_A of 1e6.
    """
    method_ids = [b""] * len(pool_tokens)
    oracles = [zero_address] * len(pool_tokens)
    for i, token in enumerate(pool_tokens):
        if token.asset_type() == 1:
            method_ids[i] = ORACLE_METHOD_ID
            oracles[i] = token.address

    with boa.env.prank(deployer), boa.reverts():
        factory.deploy_plain_pool(
            "hostile",
            "hostile",
            [t.address for t in pool_tokens],
            10**18,  # MAX_A is 10**6
            1000000,
            OFFPEG_FEE_MULTIPLIER,
            866,
            0,
            [t.asset_type() for t in pool_tokens],
            method_ids,
            oracles,
        )


@pytest.mark.only_oracle_tokens
def test_factory_rejects_fee_of_zero(deployer, factory, pool_tokens, zero_address, set_pool_implementations):
    """A pool must not be deployable with no fee.

    Nothing in the constructor or the factory places a lower bound on `_fee`. A zero
    fee removes the only cost an attacker pays to bracket a rate move, and it also
    breaks any bound derived from the fee: a cap of `2 * fee` is zero, which would
    freeze the rate permanently rather than limit it.

    Live pools already sit at the bottom of this range - two on Arbitrum charge
    0.0010%, and mainnet's `factory-stable-ng-685` charges 0.0000%.
    """
    method_ids = [b""] * len(pool_tokens)
    oracles = [zero_address] * len(pool_tokens)
    for i, token in enumerate(pool_tokens):
        if token.asset_type() == 1:
            method_ids[i] = ORACLE_METHOD_ID
            oracles[i] = token.address

    with boa.env.prank(deployer), boa.reverts():
        factory.deploy_plain_pool(
            "zerofee",
            "zerofee",
            [t.address for t in pool_tokens],
            2000,
            0,  # no fee
            OFFPEG_FEE_MULTIPLIER,
            866,
            0,
            [t.asset_type() for t in pool_tokens],
            method_ids,
            oracles,
        )
