import boa
import pytest


@pytest.fixture()
def plain_tokens(erc20_deployer, deployer, decimals):
    with boa.env.prank(deployer):
        return [erc20_deployer.deploy(f"TKN{i}", f"TKN{i}", decimals[i]) for i, d in enumerate(decimals)]


@pytest.fixture()
def oracle_tokens(erc20oracle_deployer, deployer, decimals):
    with boa.env.prank(deployer):
        return [
            erc20oracle_deployer.deploy("OTA", "OTA", 18, 1006470359024000000),
            erc20oracle_deployer.deploy("OTB", "OTB", 18, 1007580460035000000),
        ]


@pytest.fixture()
def rebase_tokens(erc20_rebasing_deployer, deployer, decimals):
    with boa.env.prank(deployer):
        return [
            erc20_rebasing_deployer.deploy(f"OR_TKN{i}", f"OR_TKN{i}", decimals[i], True)
            for i, d in enumerate(decimals)
        ]


@pytest.fixture()
def pool_tokens(pool_token_types, plain_tokens, oracle_tokens, rebase_tokens):
    tokens = {0: plain_tokens, 1: oracle_tokens, 2: rebase_tokens}
    return [tokens[t][i] for i, t in enumerate(pool_token_types)]


# <---------------------   Metapool configuration   --------------------->
@pytest.fixture()
def metapool_token(metapool_token_type, plain_tokens, oracle_tokens, rebase_tokens):
    return {0: plain_tokens, 1: oracle_tokens, 2: rebase_tokens}[metapool_token_type][0]


@pytest.fixture()
def base_pool_decimals():
    return [18, 18, 18]


@pytest.fixture()
def base_pool_tokens(erc20_deployer, deployer, base_pool_decimals):
    with boa.env.prank(deployer):
        return [erc20_deployer.deploy(c, c, base_pool_decimals[i]) for i, c in enumerate(("DAI", "USDC", "USDT"))]


@pytest.fixture()
def base_pool_lp_token(deployer, curve_token_v3_deployer):
    with boa.env.prank(deployer):
        return curve_token_v3_deployer.deploy("LP", "LP")


@pytest.fixture()
def underlying_tokens(metapool_token, base_pool_tokens, base_pool_lp_token):
    return [metapool_token, base_pool_lp_token, *base_pool_tokens]


# <---------------------   Gauge rewards  --------------------->
@pytest.fixture()
def coin_reward(owner, erc20_deployer):
    with boa.env.prank(owner):
        return erc20_deployer.deploy("CR", "CR", 18)


@pytest.fixture()
def coin_reward_a(owner, mint_owner, erc20_deployer):
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
