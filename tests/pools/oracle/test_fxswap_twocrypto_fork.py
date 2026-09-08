"""Forked-mainnet tests for the live FXSwap pools.

FXSwap is not a StableSwap-NG deployment. It is twocrypto `v3.0.0` wired to the
StableSwap math module at 0xBfDdF58C (which reports `v0.1.1`, matching
`stableswap_math_v_011.vy` as vendored into curve-core) and the FXSwap views
contract at 0x1D788b7A. Thirteen of the newest pools in the Twocrypto-NG factory
run that implementation, carrying the AUD/CAD/ZARP FX pools and Yield Basis.

These tests live here because the rate bound they check is the same one the
StableSwap-NG tests check, and the two implementations share the math module. They
would sit more naturally in twocrypto-ng; move them if that repo grows a fork suite.

Set ETH_RPC_URL to use your own archive node.
"""

import os

import boa
import pytest

# Live FXSwap pools in the Twocrypto-NG factory (0x98EE851a).
#   block  a block at which price_scale differs from block - 1
POOLS = {
    "audf_frxusd": dict(pool="0xe79fb88c7937b39b3e1cabd44faefa5258578b2d", block=25_722_386),
    "cadd_frxusd": dict(pool="0x384ca8992f955009bdd94849488e580559590157", block=25_888_430),
    "zarp_frxusd": dict(pool="0x57c881ada3fa218f8c720e10123a8b46ccc75b81", block=None),
    "cadd_usdc": dict(pool="0x4fdccb810f22578ad6700fc10a8c9b6c1df61852", block=None),
    "yield_basis_weth": dict(pool="0x656341ef90b622c6634e0573772ffb7f3669b9f3", block=None),
}

# The math module every FXSwap pool is wired to, and the version it must report.
FXSWAP_MATH = "0xbfddf58cb6ef84e115ff47c10e49a80b2653ea13"
FXSWAP_MATH_VERSION = "v0.1.1"

RPC = os.environ.get("ETH_RPC_URL", "https://eth.drpc.org")

# Minimal ABI: the twocrypto v3 source lives in curve-core, not here, and pulling it
# in would drag a 0.4.3 toolchain into this suite for six getters.
POOL_ABI = """[
 {"name":"POLICY","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"address"}]},
 {"name":"MATH","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"address"}]},
 {"name":"VIEW","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"address"}]},
 {"name":"version","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"string"}]},
 {"name":"price_scale","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"uint256"}]},
 {"name":"mid_fee","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"uint256"}]},
 {"name":"out_fee","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"uint256"}]}
]"""

MATH_ABI = """[
 {"name":"version","type":"function","stateMutability":"view","inputs":[],
  "outputs":[{"name":"","type":"string"}]}
]"""


def _at(spec, block="latest"):
    boa.fork(RPC, block_identifier=block, allow_dirty=True)
    return boa.loads_abi(POOL_ABI).at(spec["pool"])


@pytest.mark.parametrize("name", list(POOLS))
def test_policy_hook_is_configured(name):
    """Every FXSwap pool must have its POLICY wired.

    The v3 constructor sets VIEW, MATH and POLICY to `empty(address)` and expects
    them source-patched at deploy time. curve-core's open questions record that no
    Policy contract exists in that repo; it does not exist on chain either. VIEW and
    MATH did get patched, so the omission is specific to POLICY rather than the
    whole mechanism being unused.
    """
    pool = _at(POOLS[name])
    assert pool.POLICY() != "0x" + "0" * 40, f"{name}: POLICY is the zero address"


@pytest.mark.parametrize("name", list(POOLS))
def test_math_module_is_the_vendored_one(name):
    """The wired math module must be the FXSwap StableSwap math at its known version.

    Guards against a pool silently pointing at a different math implementation than
    the one vendored into curve-core and reviewed alongside it.
    """
    pool = _at(POOLS[name])
    math_addr = pool.MATH()
    assert math_addr.lower() == FXSWAP_MATH, f"{name}: unexpected math module {math_addr}"
    assert boa.loads_abi(MATH_ABI).at(math_addr).version() == FXSWAP_MATH_VERSION


@pytest.mark.parametrize("name", ["audf_frxusd", "cadd_frxusd"])
def test_price_scale_step_stays_within_two_mid_fee(name):
    """price_scale must not move further in one block than two fees can absorb.

    Measured over the 30 days to block 25,933,995, AUDF/frxUSD moves 0.036405% and
    CADD/frxUSD 0.051594% in a single block, against 2 * mid_fee of 0.0200%.

    Two caveats a reviewer should weigh before treating this as exploitable the way
    the StableSwap-NG oracle steps are. Twocrypto charges a dynamic fee between
    mid_fee and out_fee (0.01% to 0.30% on these pools), so 2 * mid_fee is the floor
    of the real bound rather than the bound. And price_scale is repegged by
    tweak_price *after* a trade, so it does not jump exogenously the way an external
    rate oracle does, and cannot be bracketed the same way.
    """
    spec = POOLS[name]
    block = spec["block"]

    boa.fork(RPC, block_identifier=block - 1, allow_dirty=True)
    before = boa.loads_abi(POOL_ABI).at(spec["pool"]).price_scale()

    boa.fork(RPC, block_identifier=block, allow_dirty=True)
    pool = boa.loads_abi(POOL_ABI).at(spec["pool"])
    after = pool.price_scale()

    move = abs(after - before) / before
    bound = 2 * pool.mid_fee() / 10**10

    assert move <= bound, (
        f"{name}: price_scale moved {move * 100:.6f}% in one block, " f"bound is {bound * 100:.4f}% (2 * mid_fee)"
    )
