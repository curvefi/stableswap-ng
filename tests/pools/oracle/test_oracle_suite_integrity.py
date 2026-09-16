"""The oracle tests themselves must be able to run, and must check what they claim.

Each failure pinned here - an API the pinned titanoboa lacks, a source read from a
git ref, a selector the oracle recovery misses, a pragma the deploy script cannot
retarget - lets a test error, skip or pass without checking anything, and no contract
test would show it.
"""

import os
import re

import boa
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))


def _oracle_test_sources():
    for name in sorted(os.listdir(HERE)):
        if name.startswith("test_") and name.endswith(".py"):
            with open(os.path.join(HERE, name), encoding="utf8") as handle:
                yield name, handle.read()


def test_fork_suites_only_call_boa_apis_that_exist():
    """Every boa.<name>(...) the oracle tests call must exist in the pinned titanoboa.

    A missing one fails with AttributeError before touching the network; boa.fork and
    boa.deal, for instance, are not in titanoboa 0.1.10.
    """
    missing = []
    for name, src in _oracle_test_sources():
        for api in sorted(set(re.findall(r"\bboa\.([a-z_]+)\(", src))):
            if not hasattr(boa, api):
                missing.append(f"{name}: boa.{api}")
    assert not missing, "called but absent from the installed titanoboa:\n  " + "\n  ".join(missing)


def test_oracle_tests_do_not_read_contract_sources_from_git():
    """No oracle test may take a contract's source from a git ref.

    CI's shallow checkout does not fetch other refs, so such a test skips there
    instead of running; and a ref like main names different code once a change merges.
    """
    this = os.path.basename(__file__)  # this file names the pattern it searches for
    offenders = [name for name, src in _oracle_test_sources() if name != this and re.search(r"git[\"',\s]+show", src)]
    assert not offenders, f"these oracle tests read sources from git: {offenders}"


# A runtime stub that answers any call with 1e18, so any selector can be registered.
ANY_SELECTOR_ORACLE = bytes.fromhex("7f" + (10**18).to_bytes(32, "big").hex() + "60005260206000f3")


@pytest.mark.parametrize("selector", ["3ba0b9a9", "679aefce", "bb7b8b80", "12345670", "abcdef00", "deadbe00"])
def test_oracle_recovery_finds_every_selector(
    selector, factory, amm_deployer, erc20_deployer, zero_address, set_pool_implementations
):
    """The rug suite's oracle recovery must find the oracle whatever its selector.

    Matching at any nibble offset lets a selector ending in a 0 nibble start half a
    byte early and swallow the real word, dropping one selector in sixteen; the
    upgradeability check then passes without checking anything.
    """
    from tests.pools.oracle.test_rug_signature_fork import _oracles

    oracles = [boa.env.generate_address() for _ in range(2)]
    for o in oracles:
        boa.env.set_code(o, ANY_SELECTOR_ORACLE)
    coins = [erc20_deployer.deploy(f"C{i}", f"C{i}", 18) for i in range(2)]
    pool = factory.deploy_plain_pool(
        "p",
        "p",
        [c.address for c in coins],
        1000,
        1_000_000,
        20_000_000_000,
        866,
        0,
        [1, 1],
        [bytes.fromhex(selector)] * 2,
        oracles,
    )
    found = {a.lower() for a in _oracles(pool)}
    assert all(o.lower() in found for o in oracles), f"selector 0x{selector}: recovered {sorted(found)}"


def test_every_pool_pragma_is_one_the_deploy_script_can_retarget():
    """The deploy script must understand every evm-version the pools declare.

    A pragma set_contract_pragma does not name passes through unchanged, so the pool
    would ship to chains without the EVM version it was built for.
    """
    with open(os.path.join(REPO, "scripts", "deploy_infra.py"), encoding="utf8") as handle:
        script = handle.read()
    begin = script.index("def set_contract_pragma")
    body = script[begin:]
    body = body[: body.index("\ndef ", 1)] if "\ndef " in body[1:] else body
    handled = set(re.findall(r"evm-version (\w+)", body))

    used = {}
    main = os.path.join(REPO, "contracts", "main")
    for name in ("CurveStableSwapNG.vy", "CurveStableSwapMetaNG.vy"):
        with open(os.path.join(main, name), encoding="utf8") as handle:
            m = re.search(r"# pragma evm-version (\w+)", handle.read())
        used[name] = m.group(1) if m else None
    unknown = {k: v for k, v in used.items() if v not in handled}
    assert not unknown, f"deploy_infra.set_contract_pragma handles {sorted(handled)}; pools declare {unknown}"
