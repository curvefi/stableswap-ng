"""Properties the oracle rate path must hold.

The rate path bounds each update to min(fee * N / (2(N - 1)), 1%) - one fee in a
two-coin pool - and keeps rated coins from moving apart by more than one bound. It
freezes rates once a block has accepted them, fails closed on a source that cannot
answer, and halts on a reading more than 5% from its anchor until poke_rates walks the
anchor back. Each test states one property in its name, so that a red test names the
defect rather than just the symptom.

Two tests are strict xfails, recording limits of the rate path rather than bugs in it:

  test_informed_prepositioning_is_not_prevented
  test_genuine_step_leaves_no_free_arbitrage_when_the_fee_is_undersized
      A bound cannot stop a trader who knows a lasting step is coming - once the pool
      reflects the step, a position taken beforehand just waits for it - and it
      cannot reprice a genuine step faster than one bound per block. The answer is
      the fee, as test_fee_sized_to_the_step_leaves_no_free_arbitrage shows. If either
      ever passes, something has changed that deserves a second look.

      Charging the lag as a fee does not work: the operator controls the lag, so it
      sizes the fee to each taker's tolerance and reopens the skim that
      test_min_dy_is_a_safety_bound_not_a_price guards.

Every pool here uses a plain token with a separate oracle contract as its rate
source. The repo's ERC20Oracle mock is its own oracle, which would let an ordinary
transfer look like an oracle call and would kill the token along with the oracle.
"""

import boa
import pytest
from boa.contracts.base_evm_contract import BoaError
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


# <---------------------   Helpers   --------------------->


def _called(computation):
    """Every address reached anywhere in a call tree."""
    seen, stack = set(), list(computation.children)
    while stack:
        c = stack.pop()
        seen.add("0x" + c.msg.code_address.hex().lower())
        stack.extend(c.children)
    return seen


def _reverts(fn):
    """True only when the call reverts on chain.

    Catching every Python exception would also swallow a renamed getter or a changed
    signature, and the assertion would hold without the call ever reaching the pool.
    """
    try:
        fn()
    except BoaError:
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


# <---------------------   Fail closed, stay exitable   --------------------->


@pytest.mark.parametrize("failure", list(BROKEN_ORACLES))
def test_broken_oracle_fails_closed(plain, failure):
    """A rate source that stops answering must halt rate-dependent paths.

    Falling back to the last healthy rate would price trades there forever, and the
    bound, comparing that rate with itself, would never move it. Halting is safe
    because proportional withdrawal needs no rate and stays open.
    """
    swap, coins, oracles, lp = plain()
    boa.env.set_code(oracles[1].address, BROKEN_ORACLES[failure])
    boa.env.time_travel(blocks=1)

    mint_for_testing(lp, 10**18, coins[0], False)
    assert _reverts(
        lambda: swap.exchange(0, 1, 10**18, 0, sender=lp)
    ), f"exchange went through with a {failure} oracle - the pool priced a coin it cannot value"
    assert _reverts(lambda: swap.get_virtual_price()), f"get_virtual_price answered with a {failure} oracle"


def test_broken_vault_fails_closed(
    factory, amm_deployer, erc20_deployer, erc4626_deployer, zero_address, set_pool_implementations
):
    """An ERC4626 coin whose vault stops answering must halt pricing too.

    Asset type 3 reads its rate through convertToAssets on the coin itself. The vault
    is the coin here, so killing it breaks transfers as well; get_virtual_price and
    stored_rates move no tokens, so a revert from them can only come from the rate read.
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
    assert _reverts(lambda: swap.stored_rates()), "stored_rates answered with a dead vault"
    assert _reverts(lambda: swap.get_virtual_price()), "get_virtual_price answered with a dead vault"


def test_withdrawals_survive_a_broken_oracle(plain):
    """Proportional remove_liquidity must keep working whatever the oracle does.

    It reads no rates. Pinned so that failing closed elsewhere can never take it away.
    """
    swap, coins, oracles, lp = plain()
    boa.env.set_code(oracles[1].address, BROKEN_ORACLES["revert"])
    boa.env.time_travel(blocks=1)

    swap.remove_liquidity(swap.balanceOf(lp) // 2, [0, 0], sender=lp)


def test_metapool_fails_closed_when_its_base_pool_does(meta):
    """If the base pool cannot report a virtual price, the metapool must not guess.

    The base's get_virtual_price is @nonreentrant, so its reverting is also how a
    read-only-reentrancy guard shows up. Falling back to a stored value would swallow
    that guard.
    """
    m, base, *_ = meta()
    boa.env.set_code(base.address, BROKEN_ORACLES["revert"])
    boa.env.time_travel(blocks=1)

    assert _reverts(lambda: m.stored_rates()), "metapool priced base LP with a base pool that cannot answer"


# <---------------------   What the bound can and cannot do   --------------------->


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
    reason="a bound below the oracle's step reprices a genuine step over several blocks, and anyone "
    "can take the gap. Charging the gap as a fee reopens the operator skim "
    "(test_min_dy_is_a_safety_bound_not_a_price); the answer is sizing the fee to the step.",
)
def test_genuine_step_leaves_no_free_arbitrage_when_the_fee_is_undersized(plain):
    """After a genuine step past the bound, a trader with no foresight profits.

    The fee and so the bound are 1 bp, against a 17 bp step. A bounded pool walks
    towards the new rate and publishes the gap for as long as it lags. Recorded as a
    cost.
    """
    swap, coins, oracles, lp = plain()
    profit = _stale_arbitrage(swap, coins, oracles[1], lp, step_bp=17)
    assert profit <= 10**15, f"a trader with no foresight took {profit / 1e18:,.2f} after a 17 bp step"


def test_fee_sized_to_the_step_leaves_no_free_arbitrage(plain):
    """A fee of at least half the oracle's step leaves nothing to take after it.

    In a two-coin pool the bound equals the fee, so the first update after the step
    closes all but step - fee of the gap, and the trade that takes the rest pays a fee
    at least that large.
    """
    swap, coins, oracles, lp = plain(fee=9_000_000)  # 9 bp, so the bound is 9 bp
    profit = _stale_arbitrage(swap, coins, oracles[1], lp, step_bp=17)
    assert profit <= 10**15, f"a fee-sized pool still left {profit / 1e18:,.2f} after a 17 bp step"


def test_transient_manipulation_is_capped(plain):
    """A rate pushed for one block must pay out no more than about one fee.

    This is what freeze plus bound buys. An attacker holding coin 1 inflates its oracle
    5% for one block, is the first to touch the pool, and sells. Unbounded, they would
    collect ~5%; bounded, they collect at most one bound less the fee. 5% is exactly
    the halt threshold, so the reading is bounded rather than halted.
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
    """Buying before a step and selling in the very next block must not pay."""
    swap, coins, oracles, lp = plain()
    swap.exchange(0, 1, 10**18, 0, sender=lp)  # anchor the cache at the pre-step rate
    boa.env.time_travel(blocks=1)
    assert _bracket(swap, coins, oracles[1], lp, step_bp=17, wait_blocks=0) <= 0


@pytest.mark.xfail(
    strict=True,
    reason="no in-pool rate limit stops a trader who knows a persistent step is coming; "
    "once the pool reflects the step, a position taken beforehand waits and sells. "
    "Mitigated by sizing the fee against the step, not by the rate path.",
)
def test_informed_prepositioning_is_not_prevented(plain):
    """Holding through the catch-up recovers the whole step. Recorded, not fixable."""
    swap, coins, oracles, lp = plain()
    swap.exchange(0, 1, 10**18, 0, sender=lp)
    boa.env.time_travel(blocks=1)
    assert _bracket(swap, coins, oracles[1], lp, step_bp=17, wait_blocks=12) <= 0


# <---------------------   Freeze on every value-moving path   --------------------->


def test_metapool_one_coin_withdrawal_freezes_the_block(meta):
    """A one-coin withdrawal must fix the rate for the rest of its block.

    Priced through the view, remove_liquidity_one_coin commits no rate and the freeze
    never engages, so an operator can reprice between two value-moving calls in one
    block.
    """
    m, base, meta_coin, base_coins, oracle, _, lp = meta()
    boa.env.time_travel(blocks=1)
    m.remove_liquidity_one_coin(m.balanceOf(lp) // 20, 0, 0, sender=lp)
    committed = m.stored_rates()[0]

    oracle.set_exchange_rate(oracle.exchangeRate() * 101 // 100)
    assert m.stored_rates()[0] == committed, "the rate moved inside the block after a one-coin withdrawal"


def test_frozen_metapool_block_does_not_call_the_oracle(meta):
    """Once a block's rate is fixed, later calls in that block must not re-fetch it.

    Fetching before checking the freeze pays for the oracle staticcall on every frozen
    call and throws the answer away, which nothing else would notice.
    """
    m, base, meta_coin, base_coins, oracle, _, lp = meta()
    boa.env.time_travel(blocks=1)
    mint_for_testing(lp, 2 * 10**18, meta_coin, False)
    m.exchange(0, 1, 10**18, 0, sender=lp)  # first touch: fixes the block's rate
    m.exchange(0, 1, 10**18, 0, sender=lp)  # frozen: should use the cache
    assert oracle.address.lower() not in _called(m._computation), "a frozen call still queried the oracle"


def test_one_coin_withdrawal_freezes_the_block(plain):
    """A one-coin withdrawal fixes the plain pool's rate for the rest of its block.

    The plain-pool counterpart of the metapool test above: without the commit, an
    operator can reprice between two value-moving calls in one block.
    """
    swap, coins, oracles, lp = plain()
    swap.remove_liquidity_one_coin(swap.balanceOf(lp) // 20, 0, 0, sender=lp)
    committed = swap.stored_rates()[1]

    oracles[1].set_exchange_rate(oracles[1].exchangeRate() * 101 // 100)
    assert swap.stored_rates()[1] == committed, "the rate moved inside the block after a one-coin withdrawal"


def test_imbalanced_withdrawal_freezes_the_block(plain):
    """An imbalanced withdrawal fixes the block's rate too.

    remove_liquidity_imbalance moves value, so it must commit like the one-coin path.
    """
    swap, coins, oracles, lp = plain()
    swap.remove_liquidity_imbalance([TVL // 100, TVL // 200], 2**256 - 1, sender=lp)
    committed = swap.stored_rates()[1]

    oracles[1].set_exchange_rate(oracles[1].exchangeRate() * 101 // 100)
    assert swap.stored_rates()[1] == committed, "the rate moved inside the block after an imbalanced withdrawal"


def test_a_frozen_block_does_not_requery_the_oracle(plain):
    """A view in a block whose rate is fixed must read the cache, not the source.

    The read-path counterpart of the metapool write-path test above.
    """
    swap, coins, oracles, lp = plain()
    swap.exchange(0, 1, 10**18, 0, sender=lp)  # first touch: fixes the block's rate

    swap.stored_rates()
    assert oracles[1].address.lower() not in _called(swap._computation), "a frozen view still queried the oracle"


# <---------------------   Bound every rate source   --------------------->


def test_the_bound_applies_to_an_erc4626_coin(
    factory, amm_deployer, erc20_deployer, erc4626_deployer, zero_address, set_pool_implementations
):
    """A vault share price is bounded like any other rate source.

    A flash donation to the vault is exactly the one-block push the bound exists for.
    Dropping asset type 3 from the bound leaves that push unbounded and no other test
    notices.
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
    mint_for_testing(lp, 10 * TVL, asset, False)
    asset.approve(vault.address, 2**256 - 1, sender=lp)
    vault.deposit(TVL, lp, sender=lp)
    mint_for_testing(lp, TVL, plain_coin, False)
    vault.approve(swap.address, 2**256 - 1, sender=lp)
    plain_coin.approve(swap.address, 2**256 - 1, sender=lp)
    swap.add_liquidity([vault.balanceOf(lp), TVL], 0, sender=lp)
    boa.env.time_travel(blocks=1)
    before = swap.stored_rates()[0]

    # a donation the vault counts as assets: its share price jumps with no shares minted
    mint_for_testing(vault.address, TVL // 50, asset, False)  # +2% of the vault
    boa.env.time_travel(blocks=1)

    moved = (swap.stored_rates()[0] - before) / before
    bound = swap.max_rate_bump() / FEE_DENOMINATOR
    assert moved <= bound + 1e-12, f"a 2% donation moved a vault coin's rate {moved * 1e4:.2f} bp in one update"


def test_two_rated_coins_cannot_be_pushed_apart(plain):
    """Two rated coins may not move apart by more than one bound in a single update.

    Bounding each coin against its own anchor lets a pair separate by two bounds when
    one source is pushed up and the other down, and the trade prices off the ratio.
    166 mainnet pools carry two rated coins. Each push is 5%, the most that is bounded
    rather than halted.
    """
    swap, coins, oracles, lp = plain(rated=(0, 1))
    before = swap.stored_rates()[0] / swap.stored_rates()[1]

    oracles[0].set_exchange_rate(oracles[0].exchangeRate() * 105 // 100)
    oracles[1].set_exchange_rate(oracles[1].exchangeRate() * 95 // 100)
    boa.env.time_travel(blocks=1)

    moved = abs(swap.stored_rates()[0] / swap.stored_rates()[1] - before) / before
    bound = swap.max_rate_bump() / FEE_DENOMINATOR
    # the pair is a ratio, so one bound each way compounds to (1 + b) / (1 - b); the
    # property is that they separate by one bound, not that the ratio moves by exactly b
    assert (
        moved <= bound * (1 + bound) + 1e-12
    ), f"an opposite push moved the pair {moved * 1e4:.2f} bp, bound {bound * 1e4:.2f} bp"


# <---------------------   Empty pools set no anchor   --------------------->


def test_dust_cannot_anchor_an_unfunded_pool(plain):
    """A dust round trip on an unfunded pool must not fix the rate the first LP pays.

    add_liquidity works on an empty pool and remove_liquidity gives the dust straight
    back. If that round trip could move the anchor freely, anyone could set the rate
    for nothing and the bound would then defend it: on an unseeded pool the first
    honest LP deposited at 1.9996 and lost 23% of their deposit in the same block.
    """
    swap, coins, oracles, attacker = plain(seed=False)
    oracles[1].set_exchange_rate(2 * 10**18)  # the push the attacker wants remembered
    swap.add_liquidity([10**6, 10**6], 0, sender=attacker)
    swap.remove_liquidity(swap.balanceOf(attacker), [0, 0], sender=attacker)
    oracles[1].set_exchange_rate(10**18)  # and released
    boa.env.time_travel(blocks=1)

    honest = boa.env.generate_address()
    for c in coins:
        mint_for_testing(honest, TVL, c, False)
        c.approve(swap.address, 2**256 - 1, sender=honest)
    swap.add_liquidity([TVL, TVL], 0, sender=honest)

    priced = swap.stored_rates()[1] / 10**18
    assert abs(priced - 1) <= 0.01, f"the first honest deposit was priced at {priced:.4f} against a true rate of 1"


def test_poke_cannot_seed_an_empty_pool(plain):
    """poke_rates must do nothing on a pool that has never been funded.

    The poke exists to walk a halted pool back to its source, and an empty pool never
    halts. Letting it write there would hand the anchor to whoever pokes first - the
    hole the test above closes.
    """
    swap, coins, oracles, lp = plain(seed=False)

    assert _reverts(lambda: swap.poke_rates()), "poke_rates wrote a rate to an unfunded pool"


# <---------------------   Bound tracks the fee   --------------------->


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
    """After the fee falls, a single update must move no further than the new bound.

    A bound fixed from the deploy fee would stay wide after a cut and leave open a
    bracket the new fee cannot pay for.
    """
    swap, coins, oracles, lp = plain(fee=4_000_000)
    step = _accepted_step(swap, 1, oracles[1], owner, new_fee=1_000_000)
    # two new fees: loose against the new 1 bp bound, still below the old 4 bp one
    bound = 2 * 1_000_000 / FEE_DENOMINATOR + 1e-12
    assert step <= bound, f"accepted {step * 1e4:.2f} bp after cutting the fee to 1 bp"


def test_metapool_fee_cut_tightens_the_bound(meta, owner):
    """The same for a metapool."""
    m, base, meta_coin, base_coins, oracle, _, lp = meta(fee=4_000_000)
    step = _accepted_step(m, 0, oracle, owner, new_fee=1_000_000)
    bound = 2 * 1_000_000 / FEE_DENOMINATOR + 1e-12
    assert step <= bound, f"accepted {step * 1e4:.2f} bp after cutting the fee to 1 bp"


@pytest.mark.parametrize("n", [2, 3, 4, 8])
def test_liquidity_round_trip_cannot_bracket_a_step(plain, n):
    """Withdrawing and re-depositing across one accepted step must not gain LP share.

    A single-sided round trip costs less than a swap round trip, and less the more
    coins the pool holds, so a bound that ignored N would leave pools of three or more
    coins a profit. The bound is fee * N / (2(N - 1)) for that reason.

    Measured at about -1.5 bp for every N here; the tolerance is +0.05 bp.
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


# <---------------------   Metapool base LP at its true value   --------------------->


def _redeemable(base, base_oracle):
    """What one base LP redeems for proportionally, at the oracle's true rate."""
    balances = base.get_balances()
    return (balances[0] * base_oracle.exchangeRate() // 10**18 + balances[1]) * 10**18 // base.totalSupply()


def _commit(m, base, meta_coin, lp):
    """Write both pools in this block, then move to the next one."""
    mint_for_testing(lp, 10**15, meta_coin, False)
    m.exchange(0, 1, 10**15, 0, sender=lp)
    boa.env.time_travel(blocks=1)


def test_metapool_bounds_a_pushed_base_pool_rate(meta):
    """A base-pool rate pushed for one block reaches the metapool as at most one bound.

    The metapool's coin 1 is the base pool's virtual price. Read live, a 5% push of the
    base's oracle moves it 250 bp and the metapool pays that out, so coin 1 has to be
    bounded like coin 0.
    """
    m, base, meta_coin, base_coins, _, base_oracle, lp = meta(meta_rated=False, base_rated=True)
    _commit(m, base, meta_coin, lp)
    before = m.stored_rates()[1]

    base_oracle.set_exchange_rate(10**18 * 105 // 100)
    move = abs(m.stored_rates()[1] - before) / before
    bound = m.max_rate_bump() / FEE_DENOMINATOR
    assert move <= bound + 1e-12, f"a 5% base-oracle push moved the metapool's base LP rate {move * 1e4:.2f} bp"


def test_metapool_freezes_the_base_pool_rate_within_a_block(meta):
    """Once a metapool block has priced base LP, the base pool must not reprice it.

    With the freeze on coin 0 only, two identical trades in one block differed by 25 bp
    when the base's oracle moved between them.
    """
    m, base, meta_coin, base_coins, _, base_oracle, lp = meta(meta_rated=False, base_rated=True)
    _commit(m, base, meta_coin, lp)
    mint_for_testing(lp, 10**15, meta_coin, False)
    m.exchange(0, 1, 10**15, 0, sender=lp)  # first touch: fixes the block's rates
    committed = m.stored_rates()[1]

    base_oracle.set_exchange_rate(10**18 * 10_050 // 10_000)
    assert m.stored_rates()[1] == committed, "the base LP rate moved inside the block after a trade"


def test_metapool_closes_a_genuine_base_step_on_its_own_writes(meta):
    """After a genuine base step, each metapool write closes the gap by a full bound.

    Bounding base LP's rate makes it trail what base LP redeems for by the part of a
    step the bound has not yet let through, and that lag is accepted, as on coin 0.
    What must not happen is a gap that stops closing: bounded at the base pool, it
    moves only when the base itself is written, so with the base idle it sat at ~49 bp
    while the metapool traded, a riskless round trip.
    """
    m, base, meta_coin, base_coins, _, base_oracle, lp = meta(meta_rated=False, base_rated=True)
    _commit(m, base, meta_coin, lp)
    bound = m.max_rate_bump() / FEE_DENOMINATOR
    start = m.stored_rates()[1]

    base_oracle.set_exchange_rate(10**18 * 101 // 100)
    boa.env.time_travel(blocks=1)
    step = (_redeemable(base, base_oracle) - start) / start
    for _ in range(20):  # the base sits idle while the metapool trades
        _commit(m, base, meta_coin, lp)

    redeemable = _redeemable(base, base_oracle)
    gap = (redeemable - m.stored_rates()[1]) / redeemable
    allowed = max(0.0, step - 20 * bound) + 1e-5
    assert gap <= allowed, (
        f"20 metapool writes after a {step * 1e4:.1f} bp base step left base LP priced "
        f"{gap * 1e4:.2f} bp below what it redeems for; at {bound * 1e4:.1f} bp a write, {allowed * 1e4:.2f} bp"
    )


def test_base_lp_lags_a_step_no_further_than_coin_0_does(meta):
    """One block after a genuine step, base LP's rate trails no further than coin 0's.

    Whatever lag a bound leaves is open to a trader with no foresight, and on coin 0 it
    is accepted at one bound per write. Coin 1 must not be a second, slower lag.
    Compared as rate gaps rather than arbitrage profits, which would also pay out
    whatever imbalance the pool started with.
    """
    m, base, meta_coin, base_coins, _, base_oracle, lp = meta(meta_rated=False, base_rated=True)
    _commit(m, base, meta_coin, lp)
    base_oracle.set_exchange_rate(10**18 * 10_034 // 10_000)  # base LP worth ~17 bp more
    boa.env.time_travel(blocks=1)
    _commit(m, base, meta_coin, lp)
    true1 = _redeemable(base, base_oracle)
    gap1 = (true1 - m.stored_rates()[1]) / true1

    m, base, meta_coin, base_coins, oracle, _, lp = meta(meta_rated=True, base_rated=False)
    _commit(m, base, meta_coin, lp)
    step = (true1 - 10**18) / 10**18  # the same step, on coin 0
    oracle.set_exchange_rate(int(10**18 * (1 + step)))
    boa.env.time_travel(blocks=1)
    _commit(m, base, meta_coin, lp)
    true0 = oracle.exchangeRate()
    gap0 = (true0 - m.stored_rates()[0]) / true0

    assert gap1 <= gap0 + 1e-5, (
        f"after a {step * 1e4:.1f} bp step and one write, base LP trails by {gap1 * 1e4:.2f} bp "
        f"against {gap0 * 1e4:.2f} bp for the same step on coin 0"
    )


# <---------------------   A collapsed reading halts, and reopens   --------------------->


def test_a_collapsed_reading_halts_rather_than_clamping(plain):
    """A reading far below its anchor halts the pool instead of being clamped in.

    Clamped, a source answering zero left the pool quoting a worthless coin at nearly
    par: 999,545 of a 1,000,000 pool paid out in one sale, because the bound walks
    towards zero one step at a time and every step still prices the coin.
    """
    swap, coins, oracles, lp = plain()
    oracles[1].set_exchange_rate(0)
    boa.env.time_travel(blocks=1)

    assert _reverts(lambda: swap.stored_rates()), "stored_rates answered for a collapsed source"
    assert _reverts(lambda: swap.get_dy(0, 1, 10**18)), "get_dy quoted a collapsed source"
    assert _reverts(lambda: swap.exchange(0, 1, 10**18, 0, sender=lp)), "a trade priced a collapsed source"
    swap.remove_liquidity(10**18, [0, 0], sender=lp)  # proportional exit reads no rates


def test_a_halted_pool_reopens_one_bound_per_poke(plain, owner):
    """`poke_rates` walks a halted pool back, one bound per block, and then it trades.

    Halting is only safe if a pool that halted on a genuine move can come back without
    governance. The walk is permissionless and paced like any other update, so the
    same bound that limits an attacker limits the recovery: a 6% step at a 0.3% fee
    takes 19 pokes.
    """
    swap, coins, oracles, lp = plain(fee=30_000_000)
    oracles[1].set_exchange_rate(10**18 * 106 // 100)
    boa.env.time_travel(blocks=1)
    assert _reverts(lambda: swap.stored_rates()), "a 6% step did not halt the pool"

    swap.poke_rates()
    assert _reverts(lambda: swap.poke_rates()), "a second poke landed in the same block"

    pokes = 1
    while pokes < 100 and _reverts(lambda: swap.stored_rates()):
        boa.env.time_travel(blocks=1)
        swap.poke_rates()
        pokes += 1

    rate, reading = swap.stored_rates()[1], oracles[1].exchangeRate()
    bound = swap.max_rate_bump() / FEE_DENOMINATOR
    assert (reading - rate) / reading <= bound, "the pool reopened further than one bound from its source"
    swap.exchange(0, 1, 10**18, 0, sender=lp)  # and it trades again


def test_the_bound_never_exceeds_its_ceiling(plain, owner):
    """However large the fee, one update may not move the rate more than BUMP_CEILING.

    The bound tracks the fee, and `set_new_fee` accepts far more than the 1% the
    factory allows at deploy. Without the ceiling a 5% fee would license a 5% move per
    block, which is the size of move the halt exists to catch.
    """
    swap, coins, oracles, lp = plain(fee=30_000_000)
    with boa.env.prank(owner):
        swap.set_new_fee(500_000_000, OFFPEG)  # 5%

    assert swap.max_rate_bump() == 10**8, "a 5% fee licensed a bound above the 1% ceiling"


# <---------------------   Empty metapools set no anchor   --------------------->


def test_empty_pool_does_not_anchor_a_manipulated_seed(meta):
    """A rate accepted while the pool holds nothing must not bind later depositors.

    A base-to-base swap is free on an empty metapool and never prices against its
    rates. If it committed coin 0's rate, anyone could move the anchor to a pushed rate
    that the first real deposit then inherits.
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


# <---------------------   No cost where nothing is rated   --------------------->


def test_pool_without_a_rate_source_keeps_no_rate_cache(plain):
    """A pool with no oracle or vault coin must not maintain a rate cache.

    Its rates are constant, so the freeze, bound and cache can change nothing - and
    on-chain they cost it about 12k gas on the first swap of every block.
    """
    swap, coins, oracles, lp = plain(rated=())
    mint_for_testing(lp, 10**18, coins[0], False)
    swap.exchange(0, 1, 10**18, 0, sender=lp)
    assert swap._storage.last_rates_block.get() == 0, "a pool with nothing rated wrote a rate cache"


# <---------------------   Deploy-time invariants   --------------------->


def test_set_new_fee_enforces_the_constructor_offpeg_rule(plain, owner):
    """The admin must not be able to set what the constructor refuses.

    The constructor rejects an offpeg multiplier that disables the off-peg brake;
    without the same check, set_new_fee could set 0 one call after deployment.
    """
    swap, *_ = plain()
    with boa.env.prank(owner):
        assert _reverts(lambda: swap.set_new_fee(swap.fee(), 0)), "set_new_fee disabled the off-peg brake"


def test_metapool_set_new_fee_enforces_the_constructor_offpeg_rule(meta, owner):
    """The same for a metapool."""
    m, *_ = meta()
    with boa.env.prank(owner):
        assert _reverts(lambda: m.set_new_fee(m.fee(), 0)), "set_new_fee disabled the off-peg brake"


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
    """A plain pool must not deploy with no math contract behind it.

    math is immutable and read from the factory at construction, so a pool deployed
    while the factory's math_implementation is unset would revert on every deposit.
    The constructor's rate seed also calls math, so the deploy reverts even without
    the explicit codesize check.
    """
    with boa.env.prank(deployer):
        bare = factory_deployer.deploy(fee_receiver, owner)
    with boa.env.prank(owner):
        bare.set_views_implementation(views_implementation.address)
        bare.set_pool_implementations(0, amm_implementation.address)
    coins = [erc20_deployer.deploy(f"C{i}", f"C{i}", 18) for i in range(2)]
    assert _reverts(
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
