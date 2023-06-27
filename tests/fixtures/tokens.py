import boa
import pytest


@pytest.fixture(scope="module")
def plain_tokens(deployer, decimals):
    tokens = []
    with boa.env.prank(deployer):
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "USDC", "USDC", decimals[0]))
        tokens.append(boa.load("contracts/mocks/ERC20.vy", "DAI", "DAI", decimals[1]))
    return tokens


@pytest.fixture(scope="module")
def weth(deployer):
    with boa.env.prank(deployer):
        return boa.load("contracts/mocks/WETH.vy")


@pytest.fixture(scope="module")
def oracle_tokens(deployer, decimals):
    tokens = []
    with boa.env.prank(deployer):
        tokens.append(
            boa.load(
                "contracts/mocks/ERC20Oracle.vy",
                "OTA",
                "OTA",
                decimals[0],
                1006470359024000000,
            )
        )
        tokens.append(
            boa.load(
                "contracts/mocks/ERC20Oracle.vy",
                "OTB",
                "OTB",
                decimals[0],
                1007580460035000000,
            )
        )
    return tokens


@pytest.fixture(scope="module")
def rebase_tokens(deployer, decimals):
    tokens = []
    with boa.env.prank(deployer):
        tokens.append(boa.load("contracts/mocks/ERC20Rebasing.vy", "downETH", "downETH", decimals[0], False))
        tokens.append(boa.load("contracts/mocks/ERC20Rebasing.vy", "stETH", "stETH", decimals[0], True))
    return tokens


@pytest.fixture(scope="module")
def pool_tokens(pool_token_types, plain_tokens, weth, oracle_tokens, rebase_tokens):
    pool_tokens = []
    for i, t in enumerate(pool_token_types):
        if t == 0:
            pool_tokens.append(plain_tokens[i])
        elif t == 1:
            pool_tokens.append(weth)
        elif t == 2:
            pool_tokens.append(oracle_tokens[i])
        elif t == 3:
            pool_tokens.append(rebase_tokens[i])
        else:
            raise ValueError("Wrong pool token type")

    return pool_tokens


@pytest.fixture(scope="module")
def coin_reward(owner):
    with boa.env.prank(owner):
        return boa.load("contracts/mocks/ERC20.vy", "CR", "CR", 18)


@pytest.fixture(scope="module")
def coin_reward_a(owner, mint_owner):
    with boa.env.prank(owner):
        return boa.load("contracts/mocks/ERC20.vy", "CRa", "CRa", 18)


@pytest.fixture(scope="module")
def coin_reward_b(owner):
    with boa.env.prank(owner):
        return boa.load("contracts/mocks/ERC20.vy", "CRb", "CRb", 18)


@pytest.fixture(scope="module")
def coin_rewards_additional(owner):
    coins = []
    with boa.env.prank(owner):
        for i in range(8):
            coins.append(boa.load("contracts/mocks/ERC20.vy", f"CR{i}", f"CR{i}", 18))

    return coins
