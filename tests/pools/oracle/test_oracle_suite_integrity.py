"""The oracle tests themselves must be able to run, and must check what they claim.

Each failure pinned here - an API the pinned titanoboa lacks, a source read from a
git ref, a selector the oracle recovery misses, a pool the deploy script
would ship to a chain that cannot run it - lets a test error, skip or pass without checking anything, and no contract
test would show it.
"""

import os
import re
import sys

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


def test_the_deploy_script_refuses_cancun_pools_on_chains_without_cancun():
    """Pools built for cancun must not ship to a chain that rejects its opcodes.

    Built for shanghai or paris they exceed the blueprint size limit, so retargeting is
    not an option: the deploy has to refuse rather than ship bytecode whose every
    nonreentrant call reverts. deploy_infra itself needs boa_zksync to import, so the
    check lives in deployment_utils and the script is only checked for calling it.
    """
    sys.path.insert(0, os.path.join(REPO, "scripts"))
    import deployment_utils

    with open(os.path.join(REPO, "scripts", "deployments.py"), encoding="utf8") as handle:
        networks = handle.read()
    # probed: both reject TLOAD, TSTORE and MCOPY as invalid opcodes. Pinned so an
    # emptied list cannot make every check below pass without running.
    assert {"polygon-zkevm", "fantom"} <= set(deployment_utils.CHAINS_WITHOUT_CANCUN)
    for chain in deployment_utils.CHAINS_WITHOUT_CANCUN:
        assert f'"{chain}:' in networks, f"{chain} is not a network the deploy scripts know"

    main = os.path.join(REPO, "contracts", "main")
    for name in ("CurveStableSwapNG.vy", "CurveStableSwapMetaNG.vy"):
        with open(os.path.join(main, name), encoding="utf8") as handle:
            source = handle.read()
        for chain in deployment_utils.CHAINS_WITHOUT_CANCUN:
            with pytest.raises(ValueError):
                deployment_utils.check_evm_version(source, f"{chain}:mainnet")
        deployment_utils.check_evm_version(source, "ethereum:mainnet")  # a cancun chain passes

    with open(os.path.join(REPO, "scripts", "deploy_infra.py"), encoding="utf8") as handle:
        script = handle.read()
    begin = script.index("def set_contract_pragma")
    body = script[begin:]
    body = body[: body.index("\ndef ", 1)]
    assert "check_evm_version(source, network)" in body, "set_contract_pragma no longer refuses unsupported chains"
