"""Properties the oracle rate path must hold, each written against a review finding.

These were written before any fix, against a rate path that had a per-update bound,
a within-block freeze and an oracle-failure fallback. The review found that design
violated most of what follows. Each test states one property in its name, and each
cites the finding it encodes, so that a red test here names the defect rather than
just the symptom.

Three tests are not like the others:

  test_transient_manipulation_is_capped
      guards the part of the design that works - freeze plus bound does stop a rate
      pushed for one block from paying out. It passes before and after any fix, and
      it must keep passing.

  test_informed_prepositioning_is_not_prevented
  test_genuine_step_leaves_no_free_arbitrage_when_the_fee_is_undersized
      are strict xfails, recording limits of the rate path rather than bugs in it. A
      bound cannot stop a trader who knows a lasting step is coming - once the pool
      reflects the step, a position taken beforehand just waits for it - and it
      cannot reprice a genuine step faster than one bound per block. Both have the
      same answer, which is the fee: test_fee_sized_to_the_step_leaves_no_free_arbitrage
      shows it. If either ever passes, the strict marker turns that into a failure,
      because something has changed that deserves a second look.

      Charging the lag as a fee was tried as a fix for the second, and removed: the
      operator controls the lag, so it sized the fee to each taker's tolerance and
      reopened the skim that test_min_dy_is_a_safety_bound_not_a_price guards.

Every pool here uses a plain token with a separate oracle contract as its rate
source. The repo's ERC20Oracle mock is its own oracle, which would let an ordinary
transfer look like an oracle call and would kill the token along with the oracle.
"""

import boa
import pytest
from eth_utils import function_signature_to_4byte_selector

from tests.utils.tokens import mint_for_testing

ORACLE_METHOD_ID = function_signature_to_4byte_selector("exchangeRate()")
FEE_DENOMINATOR = 10**10
OFFPEG = 20_000_000_000
TVL = 1_000_000 * 10**18

# Runtime bytecode for oracles that have stopped answering usefully.
BROKEN_ORACLES = {
    "revert": bytes.fromhex("60006000fd"),  # PUSH1 0, PUSH1 0, REVERT
    "empty": bytes.fromhex("00"),  # STOP: succeeds, returns nothing
    # PUSH32 2**200, PUSH1 0, MSTORE, PUSH1 32, PUSH1 0, RETURN
    "huge": bytes.fromhex("7f" + (2**200).to_bytes(32, "big").hex() + "60005260206000f3"),
    "gas_burn": bytes.fromhex("fe"),  # INVALID: consumes every unit of gas it is given
}


# ------------------------------------------------------------------ helpers


def _called(computation):
    """Every address reached anywhere in a call tree."""
    seen, stack = set(), list(computation.children)
    while stack:
        c = stack.pop()
        seen.add("0x" + c.msg.code_address.hex().lower())
        stack.extend(c.children)
    return seen


def _fails(fn):
    try:
        fn()
    except Exception:
        return True
    return False


def _plain_pool(
    factory,
    amm_deployer,
    erc20_deployer,
    erc20oracle_deployer,
    zero_address,
    n=2,
    rated=(1,),
    fee=1_000_000,
    A=1000,
    offpeg=OFFPEG,
    seed=True,
):
    """An n-coin plain pool. Coins listed in `rated` take their rate from an oracle.

    Returns (swap, coins, oracles, lp); `oracles[i]` is None for an unrated coin.
    """
    coins = [erc20_deployer.deploy(f"C{i}", f"C{i}", 18) for i in range(n)]
    oracles = [erc20oracle_deployer.deploy(f"O{i}", f"O{i}", 18, 10**18) if i in rated else None for i in range(n)]
    swap = amm_deployer.at(
        factory.deploy_plain_pool(
            "p",
            "p",
            [c.address for c in coins],
            A,
            fee,
            offpeg,
            866,
            0,
            [1 if i in rated else 0 for i in range(n)],
            [ORACLE_METHOD_ID if i in rated else b"" for i in range(n)],
            [oracles[i].address if i in rated else zero_address for i in range(n)],
        )
    )
    lp = boa.env.generate_address()
    for c in coins:
        mint_for_testing(lp, 10 * TVL, c, False)
        c.approve(swap.address, 2**256 - 1, sender=lp)
    if seed:
        swap.add_liquidity([TVL] * n, 0, sender=lp)
        boa.env.time_travel(blocks=1)
    return swap, coins, oracles, lp


def _metapool(
    factory,
    owner,
    amm_deployer,
    meta_deployer,
    erc20_deployer,
    erc20oracle_deployer,
    zero_address,
    meta_rated=True,
    base_rated=False,
    fee=1_000_000,
    seed=True,
):
    """A metapool over a fresh 2-coin NG base. Coin 0 of each may take an oracle rate.

    Returns (meta, base, meta_coin, base_coins, meta_oracle, base_oracle, lp).
    """
    base, base_coins, base_oracles, lp = _plain_pool(
        factory,
        amm_deployer,
        erc20_deployer,
        erc20oracle_deployer,
        zero_address,
        rated=(0,) if base_rated else (),
        fee=fee,
    )
    with boa.env.prank(owner):
        factory.add_base_pool(base.address, base.address, [0, 0], 2)
    meta_coin = erc20_deployer.deploy("M", "M", 18)
    meta_oracle = erc20oracle_deployer.deploy("MO", "MO", 18, 10**18) if meta_rated else None
    meta = meta_deployer.at(
        factory.deploy_metapool(
            base.address,
            "m",
            "m",
            meta_coin.address,
            1000,
            fee,
            OFFPEG,
            866,
            0,
            1 if meta_rated else 0,
            ORACLE_METHOD_ID if meta_rated else b"",
            meta_oracle.address if meta_rated else zero_address,
        )
    )
    mint_for_testing(lp, 10 * TVL, meta_coin, False)
    meta_coin.approve(meta.address, 2**256 - 1, sender=lp)
    base.approve(meta.address, 2**256 - 1, sender=lp)
    for c in base_coins:
        c.approve(meta.address, 2**256 - 1, sender=lp)
    if seed:
        meta.add_liquidity([TVL // 2, base.balanceOf(lp) // 2], 0, sender=lp)
        boa.env.time_travel(blocks=1)
    return meta, base, meta_coin, base_coins, meta_oracle, base_oracles[0], lp


@pytest.fixture()
def plain(factory, amm_deployer, erc20_deployer, erc20oracle_deployer, zero_address, set_pool_implementations):
    def build(**kw):
        return _plain_pool(factory, amm_deployer, erc20_deployer, erc20oracle_deployer, zero_address, **kw)

    return build


@pytest.fixture()
def meta(
    factory,
    owner,
    amm_deployer,
    meta_deployer,
    erc20_deployer,
    erc20oracle_deployer,
    zero_address,
    set_pool_implementations,
    set_metapool_implementations,
):
    def build(**kw):
        return _metapool(
            factory, owner, amm_deployer, meta_deployer, erc20_deployer, erc20oracle_deployer, zero_address, **kw
        )

    return build


# ---------------------------------------------- #2 #10: fail closed, stay exitable


@pytest.mark.parametrize("failure", list(BROKEN_ORACLES))
def test_broken_oracle_fails_closed(plain, failure):
    """A rate source that stops answering must halt rate-dependent paths. (#2, #10)

    The fallback this replaces priced trades at the last healthy rate forever, and the
    bound compared that rate with itself, so it never moved. Halting is what HEAD did,
    and it is the safe outcome: proportional withdrawal needs no rate and stays open.
    """
    swap, coins, oracles, lp = plain()
    boa.env.set_code(oracles[1].address, BROKEN_ORACLES[failure])
    boa.env.time_travel(blocks=1)

    mint_for_testing(lp, 10**18, coins[0], False)
    assert _fails(
        lambda: swap.exchange(0, 1, 10**18, 0, sender=lp)
    ), f"exchange went through with a {failure} oracle - the pool priced a coin it cannot value"
    assert _fails(lambda: swap.get_virtual_price()), f"get_virtual_price answered with a {failure} oracle"


def test_broken_vault_fails_closed(
    factory, amm_deployer, erc20_deployer, erc4626_deployer, zero_address, set_pool_implementations
):
    """An ERC4626 coin whose vault stops answering must halt pricing too. (#2)

    Asset type 3 reads its rate through convertToAssets on the coin itself, a path
    that also fell back to a remembered rate. The vault is the coin here, so killing
    it breaks transfers as well; get_virtual_price and stored_rates move no tokens,
    so a revert from them can only come from the rate read.
    """
    asset = erc20_deployer.deploy("A", "A", 18)
    vault = erc4626_deployer.deploy("V", "V", 18, asset.address)
    plain_coin = erc20_deployer.deploy("P", "P", 18)
    swap = amm_deployer.at(
        factory.deploy_plain_pool(
            "v",
            "v",
            [vault.address, plain_coin.address],
            1000,
            1_000_000,
            OFFPEG,
            866,
            0,
            [3, 0],
            [b"", b""],
            [zero_address, zero_address],
        )
    )
    lp = boa.env.generate_address()
    mint_for_testing(lp, TVL, asset, False)
    asset.approve(vault.address, 2**256 - 1, sender=lp)
    vault.deposit(TVL, lp, sender=lp)
    mint_for_testing(lp, TVL, plain_coin, False)
    vault.approve(swap.address, 2**256 - 1, sender=lp)
    plain_coin.approve(swap.address, 2**256 - 1, sender=lp)
    swap.add_liquidity([vault.balanceOf(lp), TVL], 0, sender=lp)
    boa.env.time_travel(blocks=1)

    boa.env.set_code(vault.address, BROKEN_ORACLES["revert"])
    boa.env.time_travel(blocks=1)
    assert _fails(lambda: swap.stored_rates()), "stored_rates answered with a dead vault"
    assert _fails(lambda: swap.get_virtual_price()), "get_virtual_price answered with a dead vault"


def test_withdrawals_survive_a_broken_oracle(plain):
    """Proportional remove_liquidity must keep working whatever the oracle does.

    This is the guarantee the fallback claimed to provide. It never needed one:
    proportional withdrawal reads no rates. Pinned so that failing closed elsewhere
    can never take it away.
    """
    swap, coins, oracles, lp = plain()
    boa.env.set_code(oracles[1].address, BROKEN_ORACLES["revert"])
    boa.env.time_travel(blocks=1)

    swap.remove_liquidity(swap.balanceOf(lp) // 2, [0, 0], sender=lp)


def test_metapool_fails_closed_when_its_base_pool_does(meta):
    """If the base pool cannot report a virtual price, the metapool must not guess. (#5)

    The base's get_virtual_price is @nonreentrant, so its reverting is also how a
    read-only-reentrancy guard shows up. Falling back to a stored value swallows that
    guard, and the stored value is never bounded.
    """
    m, base, *_ = meta()
    boa.env.set_code(base.address, BROKEN_ORACLES["revert"])
    boa.env.time_travel(blocks=1)

    assert _fails(lambda: m.stored_rates()), "metapool priced base LP with a base pool that cannot answer"


# ------------------------------------------ #1 #3: what the bound can and cannot do


def _stale_arbitrage(swap, coins, oracle, lp, step_bp):
    """Best profit from a trader with no foresight after a genuine rate step.

    The oracle steps coin 1 up by `step_bp`, a block passes, and a trader who simply
    compares stored_rates() with the oracle buys coin 1 with coin 0, valuing it at the
    oracle's true rate. Returns profit in coin-0 units.
    """
    oracle.set_exchange_rate(10**18 * (10_000 + step_bp) // 10_000)
    boa.env.time_travel(blocks=1)
    true_rate = oracle.exchangeRate()
    best = 0
    for size in (10**18, 10**21, 10**22, 5 * 10**22, 10**23, 3 * 10**23):
        with boa.env.anchor():
            arb = boa.env.generate_address()
            mint_for_testing(arb, size, coins[0], False)
            coins[0].approve(swap.address, 2**256 - 1, sender=arb)
            got = swap.exchange(0, 1, size, 0, sender=arb)
            best = max(best, got * true_rate // 10**18 - size)
    return best


@pytest.mark.xfail(
    strict=True,
    reason="#3: a bound below the oracle's step reprices a genuine step over several blocks, and anyone "
    "can take the gap. Charging the gap as a fee was tried and reopens the operator skim - the operator "
    "controls the gap, so it sizes it to the taker's tolerance (test_min_dy_is_a_safety_bound_not_a_price). "
    "The answer is sizing the fee to the step; see the test below.",
)
def test_genuine_step_leaves_no_free_arbitrage_when_the_fee_is_undersized(plain):
    """After a genuine step past the bound, a trader with no foresight profits. (#3)

    Here the fee is 1 bp, so the bound is 2 bp, against a 17 bp step. An unbounded
    pool reprices at once and leaves nothing; a bounded one walks towards the new
    rate and publishes the gap for as long as it lags. Recorded as a cost.
    """
    swap, coins, oracles, lp = plain()
    profit = _stale_arbitrage(swap, coins, oracles[1], lp, step_bp=17)
    assert profit <= 10**15, f"a trader with no foresight took {profit / 1e18:,.2f} after a 17 bp step"


def test_fee_sized_to_the_step_leaves_no_free_arbitrage(plain):
    """A fee of at least half the oracle's step leaves nothing to take after it. (#3)

    The bound is derived from the fee, so a pool whose fee covers half its oracle's
    largest step has a bound that covers the whole step: a genuine step lands in one
    update and there is no lag to arbitrage. The same fee is what makes taking a
    position ahead of the step unprofitable (#1), so one number answers both.
    """
    swap, coins, oracles, lp = plain(fee=9_000_000)  # 9 bp, so the bound is 18 bp
    profit = _stale_arbitrage(swap, coins, oracles[1], lp, step_bp=17)
    assert profit <= 10**15, f"a fee-sized pool still left {profit / 1e18:,.2f} after a 17 bp step"


def test_transient_manipulation_is_capped(plain):
    """A rate pushed for one block must pay out no more than about one fee.

    This is what freeze plus bound actually buys, and it must survive every fix. An
    attacker holding coin 1 inflates its oracle 5% for one block, is the first to
    touch the pool, and sells. Unbounded, they would collect ~5%; bounded, the pool
    accepts at most one step and they collect roughly that step less the fee.
    """
    swap, coins, oracles, lp = plain()
    atk = boa.env.generate_address()
    amount = 10**22
    mint_for_testing(atk, amount, coins[1], False)
    coins[1].approve(swap.address, 2**256 - 1, sender=atk)

    boa.env.time_travel(blocks=1)
    oracles[1].set_exchange_rate(10**18 * 105 // 100)
    got = swap.exchange(1, 0, amount, 0, sender=atk)
    oracles[1].set_exchange_rate(10**18)

    excess = (got - amount) / amount
    assert (
        excess <= 3 * swap.fee() / FEE_DENOMINATOR
    ), f"a one-block 5% oracle push paid {excess * 1e4:.2f} bp; the bound should cap it near one fee"


def _bracket(swap, coins, oracle, lp, step_bp, wait_blocks):
    """Buy before a persistent step, poke once per block for `wait_blocks`, sell back."""
    size = 10**23
    with boa.env.anchor():
        atk = boa.env.generate_address()
        mint_for_testing(atk, size + 10**20, coins[0], False)
        coins[0].approve(swap.address, 2**256 - 1, sender=atk)
        got = swap.exchange(0, 1, size, 0, sender=atk)
        oracle.set_exchange_rate(10**18 * (10_000 + step_bp) // 10_000)
        for _ in range(wait_blocks):
            boa.env.time_travel(blocks=1)
            swap.exchange(0, 1, 10**12, 0, sender=atk)
        boa.env.time_travel(blocks=1)
        coins[1].approve(swap.address, 2**256 - 1, sender=atk)
        back = swap.exchange(1, 0, got, 0, sender=atk)
    return back - size


def test_one_block_bracket_is_unprofitable(plain):
    """Buying before a step and selling in the very next block must not pay.

    The narrow claim the bound does keep. Guarded here so the fix cannot lose it.
    """
    swap, coins, oracles, lp = plain()
    swap.exchange(0, 1, 10**18, 0, sender=lp)  # anchor the cache at the pre-step rate
    boa.env.time_travel(blocks=1)
    assert _bracket(swap, coins, oracles[1], lp, step_bp=17, wait_blocks=0) <= 0


@pytest.mark.xfail(
    strict=True,
    reason="#1: no in-pool rate limit stops a trader who knows a persistent step is coming; "
    "once the pool reflects the step, a position taken beforehand waits and sells. "
    "Mitigated by sizing the fee against the step, not by the rate path.",
)
def test_informed_prepositioning_is_not_prevented(plain):
    """Holding through the catch-up recovers the whole step. Recorded, not fixable. (#1)"""
    swap, coins, oracles, lp = plain()
    swap.exchange(0, 1, 10**18, 0, sender=lp)
    boa.env.time_travel(blocks=1)
    assert _bracket(swap, coins, oracles[1], lp, step_bp=17, wait_blocks=12) <= 0


# ---------------------------------------------------- #4 #19: freeze where it belongs


def test_metapool_one_coin_withdrawal_freezes_the_block(meta):
    """A one-coin withdrawal must fix the rate for the rest of its block. (#4)

    MetaNG priced remove_liquidity_one_coin through the view, so it never committed
    a rate and the freeze never engaged; an operator could reprice between two
    value-moving calls in one block.
    """
    m, base, meta_coin, base_coins, oracle, _, lp = meta()
    boa.env.time_travel(blocks=1)
    m.remove_liquidity_one_coin(m.balanceOf(lp) // 20, 0, 0, sender=lp)
    committed = m.stored_rates()[0]

    oracle.set_exchange_rate(oracle.exchangeRate() * 101 // 100)
    assert m.stored_rates()[0] == committed, "the rate moved inside the block after a one-coin withdrawal"


def test_frozen_metapool_block_does_not_call_the_oracle(meta):
    """Once a block's rate is fixed, later calls in that block must not re-fetch it. (#19)

    MetaNG fetched first and checked the freeze after, so every frozen call still paid
    for the oracle staticcall and threw the answer away.
    """
    m, base, meta_coin, base_coins, oracle, _, lp = meta()
    boa.env.time_travel(blocks=1)
    mint_for_testing(lp, 2 * 10**18, meta_coin, False)
    m.exchange(0, 1, 10**18, 0, sender=lp)  # first touch: fixes the block's rate
    m.exchange(0, 1, 10**18, 0, sender=lp)  # frozen: should use the cache
    assert oracle.address.lower() not in _called(m._computation), "a frozen call still queried the oracle"


# -------------------------------------------------------- #6 #8: bound tracks the fee


def _accepted_step(swap, i, oracle, owner, new_fee):
    """Change the fee, step the oracle past any bound, and return the accepted step."""
    boa.env.time_travel(blocks=1)
    with boa.env.prank(owner):
        swap.set_new_fee(new_fee, OFFPEG)
    before = swap.stored_rates()[i]
    oracle.set_exchange_rate(oracle.exchangeRate() * 101 // 100)  # 1%, far past any bound
    boa.env.time_travel(blocks=1)
    return (swap.stored_rates()[i] - before) / before


def test_fee_cut_tightens_the_bound(plain, owner):
    """After the fee falls, a single update must move no further than the new bound. (#6)

    max_rate_bump was set once from the deploy fee, so cutting the fee left the bound
    at twice the old fee and reopened a bracket the new fee could not pay for.
    """
    swap, coins, oracles, lp = plain(fee=4_000_000)
    step = _accepted_step(swap, 1, oracles[1], owner, new_fee=1_000_000)
    bound = 2 * 1_000_000 / FEE_DENOMINATOR + 1e-12
    assert step <= bound, f"accepted {step * 1e4:.2f} bp after cutting the fee to 1 bp"


def test_metapool_fee_cut_tightens_the_bound(meta, owner):
    """The same for a metapool, which had no way to change its bound at all. (#6)"""
    m, base, meta_coin, base_coins, oracle, _, lp = meta(fee=4_000_000)
    step = _accepted_step(m, 0, oracle, owner, new_fee=1_000_000)
    bound = 2 * 1_000_000 / FEE_DENOMINATOR + 1e-12
    assert step <= bound, f"accepted {step * 1e4:.2f} bp after cutting the fee to 1 bp"


@pytest.mark.parametrize("n", [2, 3, 4, 8])
def test_liquidity_round_trip_cannot_bracket_a_step(plain, n):
    """Withdrawing and re-depositing across one accepted step must not gain LP share. (#8)

    2 * fee is the break-even for a swap round trip. Single-sided liquidity costs less
    per leg, so in pools of three or more coins the same bound leaves a profit of about
    fee * (1 - 2/N). The bound has to know how many coins the pool holds.

    N=2 is the control: it sits exactly at break-even, and measures about +0.01 bp from
    curvature alone. The tolerance separates that from the ~1 bp the finding is about.
    """
    swap, coins, oracles, lp = plain(n=n, rated=(0,), fee=3_000_000)
    oracles[0].set_exchange_rate(10**18 * 101 // 100)  # a real 1% step
    L = swap.balanceOf(lp) // 50
    b0 = coins[0].balanceOf(lp)
    swap.remove_liquidity_one_coin(L, 0, 0, sender=lp)
    got = coins[0].balanceOf(lp) - b0
    boa.env.time_travel(blocks=1)
    minted = swap.add_liquidity([got] + [0] * (n - 1), 0, sender=lp)
    gain = (minted - L) / L
    assert gain <= 5e-6, f"N={n}: a liquidity round trip across one step gained {gain * 1e4:+.3f} bp of LP share"


# ------------------------------------------------------- #7: base LP at its true value


def test_metapool_prices_base_lp_at_its_redeemable_value(meta):
    """A metapool's rate for base LP must match what base LP redeems for. (#7)

    The metapool reads the base's virtual price. When the base clamps a rate, that
    price trails what base LP can be proportionally redeemed for - which reads no
    rates - so base LP bought on the metapool redeems for more than it cost.

    Compared directly rather than through an arbitrage, because a rate rise also
    unbalances the metapool, and rebalancing it is ordinary arbitrage that pays out
    at HEAD too. The finding is the gap between the two valuations, not that.
    """
    m, base, meta_coin, base_coins, _, base_oracle, lp = meta(meta_rated=False, base_rated=True)
    base_oracle.set_exchange_rate(10**18 * 101 // 100)
    for _ in range(20):  # the base sits idle while the metapool trades
        boa.env.time_travel(blocks=1)
        mint_for_testing(lp, 10**18, meta_coin, False)
        m.exchange(0, 1, 10**18, 0, sender=lp)

    balances = base.get_balances()
    redeemable = (balances[0] * base_oracle.exchangeRate() // 10**18 + balances[1]) * 10**18 // base.totalSupply()
    priced = m.stored_rates()[1]
    gap = (redeemable - priced) / redeemable
    assert gap <= 1e-5, (
        f"the metapool prices base LP {gap * 1e4:.2f} bp below what it redeems for "
        f"({priced / 1e18:.6f} vs {redeemable / 1e18:.6f})"
    )


# --------------------------------------------------------- #9: no anchor while empty


def test_empty_pool_does_not_anchor_a_manipulated_seed(meta):
    """A rate accepted while the pool holds nothing must not bind later depositors. (#9)

    The first write seeds the cache unbounded, and the bound then makes it sticky. On
    an empty metapool a base-to-base swap is free and still writes, so anyone could
    seed coin 0 at a pushed rate that the first real deposit then inherits.
    """
    m, base, meta_coin, base_coins, oracle, _, lp = meta(seed=False)
    atk = boa.env.generate_address()
    mint_for_testing(atk, 10**18, base_coins[0], False)
    base_coins[0].approve(m.address, 2**256 - 1, sender=atk)

    oracle.set_exchange_rate(2 * 10**18)
    m.exchange_underlying(1, 2, 10**18, 0, sender=atk)  # base-to-base: never touches the metapool
    oracle.set_exchange_rate(10**18)
    boa.env.time_travel(blocks=1)

    assert (
        m.stored_rates()[0] <= 10**18 * 101 // 100
    ), f"an empty metapool kept a pushed seed: rate {m.stored_rates()[0] / 1e18:.4f} with the oracle at 1.0"


# ----------------------------------------------- #18: no cost where nothing is rated


def test_pool_without_a_rate_source_keeps_no_rate_cache(plain):
    """A pool with no oracle or vault coin must not maintain a rate cache. (#18)

    Its rates are constant, so the freeze, bound and cache can change nothing - and
    on-chain they cost it about 12k gas on the first swap of every block.
    """
    swap, coins, oracles, lp = plain(rated=())
    mint_for_testing(lp, 10**18, coins[0], False)
    swap.exchange(0, 1, 10**18, 0, sender=lp)
    assert swap._storage.last_rates_block.get() == 0, "a pool with nothing rated wrote a rate cache"


# --------------------------------------------------- #15 #17: deploy-time invariants


def test_set_new_fee_enforces_the_constructor_offpeg_rule(plain, owner):
    """The admin must not be able to set what the constructor refuses. (#15)

    The constructor rejects an offpeg multiplier that disables the off-peg brake,
    but set_new_fee accepted any value, including 0, one call after deployment.
    """
    swap, *_ = plain()
    with boa.env.prank(owner):
        assert _fails(lambda: swap.set_new_fee(swap.fee(), 0)), "set_new_fee disabled the off-peg brake"


def test_metapool_set_new_fee_enforces_the_constructor_offpeg_rule(meta, owner):
    """The same for a metapool. (#15)"""
    m, *_ = meta()
    with boa.env.prank(owner):
        assert _fails(lambda: m.set_new_fee(m.fee(), 0)), "set_new_fee disabled the off-peg brake"


def test_factory_without_math_cannot_deploy_a_plain_pool(
    deployer,
    owner,
    fee_receiver,
    factory_deployer,
    views_implementation,
    amm_implementation,
    erc20_deployer,
    zero_address,
):
    """A plain pool must not deploy with no math contract behind it. (#17)

    math is immutable and read from the factory at construction. Deployed while the
    factory's math_implementation is unset, the pool registers, then reverts forever
    on its first deposit.
    """
    with boa.env.prank(deployer):
        bare = factory_deployer.deploy(fee_receiver, owner)
    with boa.env.prank(owner):
        bare.set_views_implementation(views_implementation.address)
        bare.set_pool_implementations(0, amm_implementation.address)
    coins = [erc20_deployer.deploy(f"C{i}", f"C{i}", 18) for i in range(2)]
    assert _fails(
        lambda: bare.deploy_plain_pool(
            "p",
            "p",
            [c.address for c in coins],
            1000,
            1_000_000,
            OFFPEG,
            866,
            0,
            [0, 0],
            [b"", b""],
            [zero_address, zero_address],
        )
    ), "a plain pool deployed with no math implementation"
