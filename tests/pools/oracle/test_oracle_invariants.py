"""Invariants the oracle path holds, pinned so a change has to be deliberate.

These were written against the unbounded implementation, before the rate path grew a
per-update bound and a cached `last_rates`. Both touch how a rate reaches `xp`, and
the cheapest way for such work to go
wrong is silently: a scaling factor dropped, a view and its executing counterpart
drifting apart, a plain coin picking up a rate it should never have.

Four of them did break, and the break was the point. `stored_rates()` no longer
reflects an oracle that moved in the *same block* - that is the freeze, and it is what
stops a trade being repriced after it was quoted. The properties themselves still
hold; they hold one block later. Those tests now advance a block before reading, and
say so, because the alternative reading - deleting them - would throw away the only
place the new timing is written down.

One test changed meaning rather than timing, and is renamed for it: a source that
answers zero is a successful answer, so the bound walks the rate towards it rather
than rejecting it. A source that fails outright - reverts, or returns nothing - halts
the pool instead; that is pinned in `test_rate_safety.py`.
"""

import boa
import pytest

from tests.utils.tokens import mint_for_testing

pytestmark = pytest.mark.usefixtures("initial_setup")


def _oracle_coin(pool_tokens):
    for i, token in enumerate(pool_tokens):
        if token.asset_type() == 1:
            return i
    pytest.skip("no oracle-backed coin in this pool")


@pytest.mark.only_oracle_tokens
def test_stored_rate_is_the_oracle_value_scaled_by_decimals(swap, pool_tokens, decimals):
    """`stored_rates` is the oracle reading scaled to 1e36 / 10**decimals.

    The scaling is what lets coins of different decimals share one invariant, so it
    is the first thing to check after any change to how rates are fetched.
    """
    i = _oracle_coin(pool_tokens)
    multiplier = 10 ** (36 - decimals[i])
    expected = multiplier * pool_tokens[i].exchange_rate() // 10**18
    assert swap.stored_rates()[i] == expected


@pytest.mark.only_oracle_tokens
def test_stored_rate_follows_the_oracle(swap, pool_tokens, decimals):
    """A moved oracle moves the stored rate - from the next block, and bounded.

    It no longer moves proportionally, and it no longer moves at all inside the block
    the oracle changed in. What must survive is the direction and the fact that the
    rate tracks its oracle at all; a rate that stopped following would be a pool
    permanently priced at whatever it last accepted.
    """
    i = _oracle_coin(pool_tokens)
    before = swap.stored_rates()[i]

    rate = pool_tokens[i].exchange_rate()
    pool_tokens[i].set_exchange_rate(rate * 2)

    assert swap.stored_rates()[i] == before, "the rate moved inside the block"

    boa.env.time_travel(blocks=1)
    after = swap.stored_rates()[i]
    assert after > before, "stored rate did not follow the oracle on the next block"
    assert (
        after <= before + before * swap.max_rate_bump() // 10**10
    ), "a single update moved further than max_rate_bump allows"


@pytest.mark.only_plain_tokens
def test_plain_coin_rate_is_a_pure_decimal_multiplier(swap, pool_tokens, decimals):
    """A coin with no oracle carries the decimal multiplier and nothing else.

    Anything that reads back differently means a plain coin has acquired a rate,
    which would put it under whatever bound applies to oracle-backed coins.
    """
    for i, _ in enumerate(pool_tokens):
        assert swap.stored_rates()[i] == 10 ** (36 - decimals[i])


@pytest.mark.only_oracle_tokens
def test_raising_the_output_rate_reduces_what_a_taker_receives(swap, pool_tokens, decimals):
    """Rates enter pricing in the direction the invariant expects.

    Raising the rate of the coin being bought makes each unit count for more inside
    `xp`, so fewer units come back out. A rework that inverts this would leave the
    pool quoting backwards while every balance still looked correct.
    """
    receiving = _oracle_coin(pool_tokens)
    sending = 1 - receiving
    amount = 1_000 * 10 ** decimals[sending]

    before = swap.get_dy(sending, receiving, amount)
    pool_tokens[receiving].set_exchange_rate(pool_tokens[receiving].exchange_rate() * 101 // 100)

    # the rate is frozen within the block the oracle moved in
    boa.env.time_travel(blocks=1)
    after = swap.get_dy(sending, receiving, amount)

    assert after < before, "raising the output coin's rate did not reduce dy"


@pytest.mark.only_oracle_tokens
def test_quote_matches_execution_when_the_oracle_holds_still(bob, swap, pool_tokens, decimals):
    """`get_dy` and `exchange` agree while nothing moves between them.

    They read rates through separate paths, so this is what catches the two drifting
    apart - a cache updated on one side only, say, or a bound applied to the view
    but not to the trade.
    """
    receiving = _oracle_coin(pool_tokens)
    sending = 1 - receiving
    amount = 1_000 * 10 ** decimals[sending]

    mint_for_testing(bob, amount, pool_tokens[sending])
    quoted = swap.get_dy(sending, receiving, amount)
    filled = swap.exchange(sending, receiving, amount, 0, sender=bob)

    assert filled == quoted, f"quote {quoted} but fill {filled} with nothing moving between"


@pytest.mark.only_oracle_tokens
def test_virtual_price_follows_a_rate_increase(swap, pool_tokens):
    """A higher rate on a held coin raises the pool's virtual price.

    `get_virtual_price` prices LP shares off the same rates, so it is the path by
    which a rate reaches anything downstream that values LP tokens.
    """
    i = _oracle_coin(pool_tokens)
    before = swap.get_virtual_price()

    pool_tokens[i].set_exchange_rate(pool_tokens[i].exchange_rate() * 101 // 100)

    # the rate is frozen within the block the oracle moved in
    boa.env.time_travel(blocks=1)
    assert swap.get_virtual_price() > before


@pytest.mark.only_oracle_tokens
def test_a_zero_rate_answer_moves_the_rate(swap, pool_tokens):
    """A source that answers zero must not be absorbed into the healthy rate.

    Zero is a successful 32-byte answer, not a failure, so the pool does not halt on
    it - the bound walks the accepted rate towards it one step per block instead.
    What must never happen is that answer being swallowed, leaving the pool reading
    identically before and after its source went bad.

    A source that fails outright is a different case and halts the pool; see
    test_broken_oracle_fails_closed in test_rate_safety.py.
    """
    i = _oracle_coin(pool_tokens)
    healthy = swap.stored_rates()[i]

    with boa.env.anchor():
        pool_tokens[i].set_exchange_rate(0)
        boa.env.time_travel(blocks=1)
        assert swap.stored_rates()[i] != healthy, "a zero answer read as the healthy rate"
