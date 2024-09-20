import boa
import pytest

from tests.constants import TOKEN_TYPES
from tests.fixtures.accounts import mint_account


@pytest.fixture()
def plain_tokens(erc20_deployer, deployer, decimals):
    with boa.env.prank(deployer):
        return [
            erc20_deployer.deploy(f"TKN{i}", f"TKN{i}", decimals[i]) for i, d in enumerate(decimals)
        ]


@pytest.fixture()
def oracle_tokens(erc20oracle_deployer, deployer, decimals):
    with boa.env.prank(deployer):
        return [
            erc20oracle_deployer.deploy("OTA", "OTA", 18, 1006470359024000000),
            erc20oracle_deployer.deploy("OTB", "OTB", 18, 1007580460035000000),
        ]


@pytest.fixture()
def rebasing_tokens(erc20_rebasing_deployer, deployer, decimals):
    with boa.env.prank(deployer):
        return [
            erc20_rebasing_deployer.deploy(f"OR_TKN{i}", f"OR_TKN{i}", decimals[i], True)
            for i, d in enumerate(decimals)
        ]


@pytest.fixture()
def pool_tokens(pool_token_types, request, initial_decimals):
    assert initial_decimals, "Fixture required for requesting `decimals` downstream"
    fixtures = {
        TOKEN_TYPES["plain"]: "plain_tokens",
        TOKEN_TYPES["oracle"]: "oracle_tokens",
        TOKEN_TYPES["rebasing"]: "rebasing_tokens",
    }
    type1, type2 = pool_token_types
    first, _ = request.getfixturevalue(fixtures[type1])
    _, second = request.getfixturevalue(fixtures[type2])
    return [first, second]


# <---------------------   Metapool configuration   --------------------->
@pytest.fixture()
def metapool_token(metapool_token_type, request, initial_decimals, pool_token_types):
    assert (
        initial_decimals and pool_token_types
    ), "Fixtures required for requesting `decimals` downstream"
    fixture = {
        TOKEN_TYPES["plain"]: "plain_tokens",
        TOKEN_TYPES["oracle"]: "oracle_tokens",
        TOKEN_TYPES["rebasing"]: "rebasing_tokens",
    }
    if metapool_token_type is not None:
        metapool_token, _ = request.getfixturevalue(fixture[metapool_token_type])
    else:
        metapool_token = None
    return metapool_token


@pytest.fixture()
def base_pool_decimals():
    return [18, 18, 18]


@pytest.fixture()
def base_pool_tokens(erc20_deployer, deployer, base_pool_decimals):
    with boa.env.prank(deployer):
        return [
            erc20_deployer.deploy(c, c, base_pool_decimals[i])
            for i, c in enumerate(("DAI", "USDC", "USDT"))
        ]


@pytest.fixture()
def base_pool_lp_token(deployer, curve_token_v3_deployer):
    with boa.env.prank(deployer):
        return curve_token_v3_deployer.deploy("LP", "LP")


@pytest.fixture()
def underlying_tokens(metapool_token, base_pool_tokens, base_pool_lp_token):
    if metapool_token is not None:
        return [metapool_token, base_pool_lp_token, *base_pool_tokens]
    else:
        return []


# <---------------------   Gauge rewards  --------------------->
@pytest.fixture()
def coin_reward(owner, erc20_deployer):
    with boa.env.prank(owner):
        return erc20_deployer.deploy("CR", "CR", 18)


@pytest.fixture()
def coin_reward_a(owner, erc20_deployer, pool_tokens, initial_balance, initial_amounts):
    mint_account(owner, pool_tokens, initial_balance, initial_amounts)
    with boa.env.prank(owner):
        return erc20_deployer.deploy("CRa", "CRa", 18)


@pytest.fixture()
def coin_reward_b(owner, erc20_deployer):
    with boa.env.prank(owner):
        return erc20_deployer.deploy("CRb", "CRb", 18)


@pytest.fixture()
def coin_rewards_additional(owner, erc20_deployer):
    with boa.env.prank(owner):
        return [erc20_deployer.deploy(f"CR{i}", f"CR{i}", 18) for i in range(8)]
