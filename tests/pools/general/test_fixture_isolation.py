"""A function-scoped fixture's changes to the chain must not outlive its test.

titanoboa anchors every fixture and unwinds them in reverse. Module-scoped fixtures
that are first created lazily, inside a function-scoped chain, sit above that test's
own function fixtures on the anchor stack - and then the function fixtures' changes
are not unwound when the test ends. The contract state is, but block number and
timestamp are not.

This has to be its own module: the leak needs these tests to be the first to trigger
the module-scoped implementation fixtures.
"""

import boa
import pytest

SEEN = {}


@pytest.fixture()
def jumps_the_chain():
    boa.env.time_travel(blocks=1000)
    return boa.env.evm.patch.block_number


def test_0_record_the_starting_block(
    amm_deployer,
    meta_deployer,
    factory_deployer,
    views_deployer,
    math_deployer,
    gauge_deployer,
    erc20_deployer,
    erc20oracle_deployer,
    erc20_rebasing_deployer,
    pool_size,
    zero_address,
    initial_balance,
):
    """Create every session fixture the pool chain uses, before the test that moves the chain.

    Any longer-lived fixture created lazily inside a test's fixture chain traps that
    test's function fixtures on titanoboa's anchor stack - session fixtures included,
    and that part predates this change. Creating them all here leaves the
    module-scoped implementations as the only thing that could still be created
    late, which is what this module isolates.
    """
    SEEN["start"] = boa.env.evm.patch.block_number


@pytest.mark.only_basic_pool
@pytest.mark.only_plain_tokens
def test_1_a_fixture_moves_the_chain(jumps_the_chain, swap):
    SEEN["jumped_to"] = jumps_the_chain


def test_2_the_move_does_not_leak():
    """(#20) With module-scoped implementations, block 1001 leaked into this test."""
    if "jumped_to" not in SEEN:
        pytest.skip("depends on the previous test having run first")
    assert boa.env.evm.patch.block_number == SEEN["start"], (
        f"a fixture's time_travel leaked: block {boa.env.evm.patch.block_number}, "
        f"started at {SEEN['start']}, fixture moved to {SEEN['jumped_to']}"
    )
