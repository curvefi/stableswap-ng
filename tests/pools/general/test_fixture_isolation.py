"""A function fixture's block/timestamp changes must not outlive its test.

They leak when a module-scoped fixture is first created inside that test's fixture chain, so this
module must be the first thing to request the implementations.
"""

import boa
import pytest

SEEN = {}


@pytest.fixture()
def jumps_the_chain():
    boa.env.time_travel(blocks=1000)
    return boa.env.evm.patch.block_number


# requests the session fixtures up front, so only the module-scoped implementations can still be created late
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
    SEEN["start"] = boa.env.evm.patch.block_number


@pytest.mark.only_basic_pool
@pytest.mark.only_plain_tokens
def test_1_a_fixture_moves_the_chain(jumps_the_chain, swap):
    SEEN["jumped_to"] = jumps_the_chain


def test_2_the_move_does_not_leak():
    if "jumped_to" not in SEEN:
        pytest.skip("depends on the previous test having run first")
    assert boa.env.evm.patch.block_number == SEEN["start"], (
        f"a fixture's time_travel leaked: block {boa.env.evm.patch.block_number}, "
        f"started at {SEEN['start']}, fixture moved to {SEEN['jumped_to']}"
    )
