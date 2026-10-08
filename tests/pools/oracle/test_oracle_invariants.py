"""Invariants the oracle path holds, pinned so a change has to be deliberate.

Changes to how a rate reaches `xp` tend to go wrong silently: a scaling factor
dropped, a view and its executing counterpart drifting apart, a plain coin picking up
a rate it should never have.

Rates are frozen within a block, so a test that moves an oracle advances a block
before reading. The bound, the halt and failing sources are pinned in
`test_rate_safety.py`.
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

    A rate that stopped following would leave the pool permanently priced at
    whatever it last accepted.
    """
    i = _oracle_coin(pool_tokens)
    before = swap.stored_rates()[i]

    # 2% stays inside HALT_THRESHOLD, so the bound walks towards it rather than halting
    rate = pool_tokens[i].exchange_rate()
    pool_tokens[i].set_exchange_rate(rate * 102 // 100)

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

    They read rates through separate paths, so this catches a cache updated on one
    side only, or a bound applied to the view but not to the trade.
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
def test_a_zero_rate_answer_halts_the_pool(swap, pool_tokens):
    """A source that answers zero must halt the rate path rather than be clamped into it.

    Zero is a successful 32-byte answer, not a failed call. Walking the rate towards
    it one bound per block would quote a collapsed coin near par for as long as the
    walk took; a reading more than 5% from its anchor halts instead.
    """
    i = _oracle_coin(pool_tokens)

    with boa.env.anchor():
        pool_tokens[i].set_exchange_rate(0)
        boa.env.time_travel(blocks=1)
        with boa.reverts():
            swap.stored_rates()
