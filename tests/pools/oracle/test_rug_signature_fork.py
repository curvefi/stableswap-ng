"""Forked-Arbitrum record of the operator-controlled-oracle pool signature.

These assert properties of fourteen pools already deployed on the Arbitrum factory,
through their own bytecode, and are marked xfail: no change in this repository
reaches them. The parts of this shape a pool can refuse are pinned against this
repository's code in test_operator_skim.py and test_rate_safety.py. The fourteen
share:

  * both coins priced by a `getRate()` oracle that is an upgradeable proxy, all
    fourteen pointing at a single beacon whose owner is an EOA. Whoever holds that
    key decides what every rate returns, including returning nothing.
  * `A = 100000`, which flattens the invariant so a rate move reaches more value.
  * `offpeg_fee_multiplier = 0`, at or below FEE_DENOMINATOR, so `_dynamic_fee`
    returns the base fee and trading a dislocated pool stays cheap.

The pairs are not stablecoin pairs - USDC/WETH, WBTC/USDC, ARB/USDC, wstETH/WETH -
so the oracle was the only thing setting the price. All fourteen revert out of
`stored_rates()`, which also hides them from any screen that classifies pools by
reading it.

They were deployed that way: the first block with code already reverts.

    usdc_usdt     371,290,609    revert
    usdc_weth_a   368,706,180    revert
    wsteth_weth   379,177,058    revert
    arb_usdc      378,485,405    revert

Having never priced, failing closed is correct for them; a fallback that let them
trade would invent a price for assets they have never been able to value.

Set ARBITRUM_RPC_URL to use your own archive node.
"""

import os
import re

import boa
import pytest

RPC = os.environ.get("ARBITRUM_RPC_URL", "https://arbitrum-one.public.blastapi.io")

# titanoboa 0.1.10's boa.env.fork rewrites the env in place, pulling state out from
# under the boa plugin's fixture anchors so they fail to unwind at teardown. Each
# test manages its own chain state, so the plugin's isolation is switched off.
pytestmark = [
    pytest.mark.ignore_isolation,
    pytest.mark.xfail(
        reason=(
            "asserts properties of pools already deployed on Arbitrum; titanoboa's .at() binds the ABI to "
            "the deployed bytecode, so no change in this repository can make these pass"
        ),
        strict=False,
    ),
]

FEE_DENOMINATOR = 10**10

# The cluster, all on the Arbitrum StableSwap-NG factory 0x9AF14D26.
POOLS = {
    "usdc_weth_a": "0xf9ae77094ae7308debf9ea25aeb3c8ab55714f32",
    "wbtc_usdc": "0x2e6cfeeb00038f6a88a008e8b3c2bbd2f6c6bf9f",
    "usdc_usdt": "0x8afce00f46938db8e958fa7f8a1f4626c26242b7",
    "usdc_weth_b": "0x985af736fb71fe2d9275c06f2d4dac7e3045fc02",
    "arb_usdc": "0xc1005bbafa47f8aeb084646ffd83fd8dada3bb3b",
    "wbtc_usdt": "0xc5f069dd8112614673890aa21d8989d5d0db69d8",
    "usdc_dai": "0x65ca82b7e64fcecbea3939b26ee7cf2cc6a2768c",
    "dai_usdt": "0x9472d4d1eb84f455eddcd7f4a0625398bd237ad0",
    "wbtc_weth": "0xc55be2dc490578560a030b6ba387aba0fe03cc73",
    "weth_usdt": "0x533482d1d126ad8dd1ed925655b717a3425adf39",
    "weth_arb": "0x4f4dcb8d373c26cc7db78ad1dc5ffdfcb45f4e55",
    "wsteth_weth": "0x16c83de64a7e91522c23f14832e0129eb9a73164",
    "usdc_usdt_b": "0x2b7dcdc718e03749de0a138c56b0e18f9750134b",
    "usdc_usdt_c": "0x2ff3ba10deb05573d2fae704a962183461d106d8",
}

# rate_oracles is packed [4-byte method_id][8 zero bytes][20-byte address] and stored
# as a Vyper immutable, so it can be recovered from the pool's runtime code.
ORACLE_WORD = re.compile("([0-9a-f]{8})" + "0" * 16 + "([0-9a-f]{40})")

# implementation() and the EIP-1967 implementation slot: either means the code the
# oracle runs can be swapped after the pool committed to the address.
PROXY_MARKERS = ("5c60da1b", "360894a1")


@pytest.fixture(scope="module")
def swap_deployer():
    return boa.load_partial("contracts/main/CurveStableSwapNG.vy")


def _fork():
    boa.env.fork(RPC, block_identifier="latest")


def _oracles(address):
    """Recover the pool's rate oracle addresses from its immutables.

    Vyper appends immutables to the runtime code as whole 32-byte words, so words
    are read aligned from the end of the code. Matching at any offset would let a
    selector ending in a 0 nibble start half a byte early and swallow the real word.
    """
    code = boa.env.get_code(address).hex().lower()
    found = set()
    for end in range(len(code), 63, -64):
        start = end - 64
        word = ORACLE_WORD.fullmatch(code[start:end])
        if word and word.group(1) != "0" * 8 and not word.group(2).startswith("0" * 30):
            found.add("0x" + word.group(2))
    return sorted(found)


@pytest.mark.parametrize("name", list(POOLS))
def test_rate_oracle_is_not_upgradeable(name):
    """A pool must not price itself off code someone can swap out later.

    The pool commits to an oracle address at deploy time and can never change it,
    so an upgradeable oracle hands the proxy admin permanent authority over the
    pool's prices. Here one EOA holds that authority over all fourteen.
    """
    _fork()
    address = POOLS[name]
    upgradeable = []
    for oracle in _oracles(address):
        code = boa.env.get_code(oracle).hex().lower()
        if any(marker in code for marker in PROXY_MARKERS):
            upgradeable.append(oracle)
    assert not upgradeable, f"{name}: rate priced by upgradeable oracle(s) {upgradeable}"


@pytest.mark.parametrize("name", list(POOLS))
def test_offpeg_fee_escalation_is_enabled(name):
    """The off-peg fee must actually escalate.

    `_dynamic_fee` returns the base fee untouched whenever the multiplier is at or
    below FEE_DENOMINATOR, so a zero here removes the pool's only defence against
    being traded while dislocated — exactly the state a moved oracle creates.
    """
    _fork()
    pool = boa.loads_abi(
        '[{"name":"offpeg_fee_multiplier","type":"function","stateMutability":"view",'
        '"inputs":[],"outputs":[{"name":"","type":"uint256"}]}]'
    ).at(POOLS[name])
    multiplier = pool.offpeg_fee_multiplier()
    assert (
        multiplier > FEE_DENOMINATOR
    ), f"{name}: offpeg_fee_multiplier is {multiplier}, so the dynamic fee never rises"


@pytest.mark.parametrize("name", list(POOLS))
def test_pricing_survives_oracle_failure(swap_deployer, name):
    """Records that a reverting oracle takes every rate-dependent path down.

    A reverting oracle propagates through `stored_rates` into `get_dy`,
    `get_virtual_price`, `calc_withdraw_one_coin` and every exchange path, while
    balances keep answering, so proportional `remove_liquidity` is the only exit.

    The assertion is the property these pools lack, not a target: for a source that
    has never priced, failing closed is correct, and this repository's pools also
    fail closed on a broken source rather than falling back to a stale rate.
    """
    _fork()
    pool = swap_deployer.at(POOLS[name])
    pool.get_balances()  # unaffected, and proves the pool itself is reachable

    try:
        pool.get_virtual_price()
    except Exception as exc:
        pytest.fail(f"{name}: get_virtual_price reverts through the oracle - {type(exc).__name__}")
