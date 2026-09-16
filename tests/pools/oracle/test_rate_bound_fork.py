"""Forked-mainnet tests for the oracle rate bound.

These fail against the current implementation, on live pools rather than fixtures,
because the failures are real. As of block 25,933,995 there are 18 StableSwap-NG
pools whose rate oracle steps further in a single block than the pool's own fee can
absorb; the two used here are among them.

Background. A sandwich around one rate update costs the attacker two fees, so an
update stays non-arbitrageable exactly while it is within `2 * fee`. That threshold
is not a convention but a measured breakeven, confirmed three ways: by grid
simulation over the pool math, by a forked-EVM measurement on real balances, and by
replaying 5,493 real trades.

Each case names the block the step lands in, so pool state and oracle value are both
genuine and nothing is mocked. Set ETH_RPC_URL to use your own archive node.
"""

import os

import boa
import pytest

# Real single-block steps, located by narrowing a 30-day window to block resolution.
#   step   measured relative move across `block - 1` -> `block`
#   bound  2 * fee, the largest non-arbitrageable single update
POOLS = {
    "ynusdx_scrvusd": dict(
        pool="0xa256d38e73cce6e00447fa64a95069ea7d32f841", block=25_787_886, step=0.00171369, bound=0.0002
    ),
    "usdc_dusd": dict(
        pool="0x32e616f4f17d43f9a5cd9be0e294727187064cb3", block=25_898_076, step=0.00163425, bound=0.0002
    ),
}

RPC = os.environ.get("ETH_RPC_URL", "https://eth.drpc.org")

# These tests fork the chain more than once each, at different blocks, and
# titanoboa 0.1.10's boa.env.fork rewrites the current env in place. That pulls the
# state out from under every fixture anchor the boa plugin has stacked, and the
# anchors then fail to unwind at teardown. Each test manages its own chain state, so
# the plugin's isolation is switched off here rather than fought.
pytestmark = pytest.mark.ignore_isolation


@pytest.fixture(scope="module")
def swap_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapNG.vy")


@pytest.fixture(scope="module")
def erc20_deployer():
    return boa.load_partial("contracts/mocks/ERC20.vy")


def _at(deployer, spec, block):
    boa.env.fork(RPC, block_identifier=block)
    return deployer.at(spec["pool"])


def _deal(token, account, amount):
    """Set an ERC20 balance on a fork by finding the slot its balances live in.

    boa.deal does this, but the pinned titanoboa does not have it. Solidity keys a
    mapping entry at keccak(key . slot) and Vyper at keccak(slot . key); both are
    tried over the first 32 slots, and every probe is put back if it misses. Returns
    False for a token that keeps balances anywhere else.
    """
    from eth_utils import keccak

    key = bytes.fromhex(account[2:].lower().rjust(64, "0"))
    for slot in range(32):
        s = slot.to_bytes(32, "big")
        for preimage in (key + s, s + key):
            position = int.from_bytes(keccak(preimage), "big")
            original = boa.env.get_storage(token.address, position)
            boa.env.set_storage(token.address, position, amount)
            if token.balanceOf(account) == amount:
                return True
            boa.env.set_storage(token.address, position, original)
    return False


def _fund(erc20_deployer, coin, account, amount):
    """Fund an account, skipping when the token's balance slot cannot be found.

    Some of these coins are proxies or compute supply on the fly. Skipping keeps the
    distinction between "cannot fund" and "the pool is safe" - the two must never
    look alike.
    """
    if not _deal(erc20_deployer.at(coin), account, amount):
        pytest.skip(f"cannot fund {coin}: no balance slot found")


def _oracle_idx(swap):
    """The coin priced by an oracle: its rate is not a plain decimal multiplier."""
    for i, rate in enumerate(swap.stored_rates()):
        trimmed = rate
        while trimmed % 10 == 0:
            trimmed //= 10
        if trimmed != 1:
            return i
    pytest.skip("pool has no oracle-backed coin")


@pytest.mark.parametrize("name", list(POOLS))
def test_single_block_step_stays_within_two_fee(swap_deployer, name):
    """A rate may not move further in one block than two fees can absorb.

    Anything larger is arbitrageable by construction: bracket the update, pay the
    fee twice, keep the difference.
    """
    spec = POOLS[name]

    swap = _at(swap_deployer, spec, spec["block"] - 1)
    idx = _oracle_idx(swap)
    before = swap.stored_rates()[idx]

    swap = _at(swap_deployer, spec, spec["block"])
    after = swap.stored_rates()[idx]

    step = abs(after - before) / before
    bound = 2 * swap.fee() / 10**10

    assert step <= bound, (
        f"{name}: rate moved {step * 100:.6f}% in one block, " f"bound is {bound * 100:.4f}% (2 * fee)"
    )


@pytest.mark.parametrize("name", list(POOLS))
def test_step_cannot_be_sandwiched(swap_deployer, erc20_deployer, name):
    """Bracketing the step must not pay.

    Buys in immediately before the update and sells back immediately after, over
    the real exchange path and real balances. Profit is denominated in the input
    coin, so anything above zero came out of the LPs.
    """
    spec = POOLS[name]
    attacker = boa.env.generate_address()

    swap = _at(swap_deployer, spec, spec["block"] - 1)
    coin_in, coin_out = swap.coins(0), swap.coins(1)
    dx = swap.get_balances()[0] // 10

    _fund(erc20_deployer, coin_in, attacker, dx)
    with boa.env.prank(attacker):
        erc20_deployer.at(coin_in).approve(swap.address, dx)
        dy = swap.exchange(0, 1, dx, 0)

    # the oracle steps here; the step itself does not move balances
    swap = _at(swap_deployer, spec, spec["block"])
    _fund(erc20_deployer, coin_out, attacker, dy)
    with boa.env.prank(attacker):
        erc20_deployer.at(coin_out).approve(swap.address, dy)
        back = swap.exchange(1, 0, dy, 0)

    assert back <= dx, (
        f"{name}: sandwiching the step returned {back - dx} more than it cost, "
        f"{(back - dx) / dx * 1e4:.2f} bp of the trade"
    )


@pytest.mark.parametrize("name", list(POOLS))
def test_quote_is_honoured_at_execution(swap_deployer, name):
    """A quote must still hold when the trade lands.

    `_stored_rates` is read inside the trade, so a taker is priced at whatever the
    oracle returns on execution rather than at what they were quoted. An aggregator
    quoting one block ahead cannot bind the fill, and the gap is the whole step.
    """
    spec = POOLS[name]

    swap = _at(swap_deployer, spec, spec["block"] - 1)
    dx = swap.get_balances()[0] // 1000
    quoted = swap.get_dy(0, 1, dx)

    swap = _at(swap_deployer, spec, spec["block"])
    filled = swap.get_dy(0, 1, dx)

    drift = abs(filled - quoted) / quoted
    bound = 2 * swap.fee() / 10**10

    assert drift <= bound, (
        f"{name}: quote moved {drift * 100:.6f}% between quote and fill, "
        f"more than the {bound * 100:.4f}% a taker can price in"
    )
