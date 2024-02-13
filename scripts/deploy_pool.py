import os
import sys
from dataclasses import dataclass
from typing import List

import boa
from boa.network import NetworkEnv
from deployment_utils import FIDDYDEPLOYER
from eth_account import Account
from eth_typing import Address
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

deployments = {
    # Ethereum
    "ethereum:sepolia": {"factory": "0xfb37b8D939FFa77114005e61CFc2e543d6F49A81"},
    "ethereum:mainnet": {"factory": "0x6A8cbed756804B16E05E741eDaBd5cB544AE21bf"},
    # Layer 2
    "arbitrum:mainnet": {"factory": "0x9AF14D26075f142eb3F292D5065EB3faa646167b"},
    "optimism:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E"},
    "base:mainnet": {"factory": "0xd2002373543Ce3527023C75e7518C274A51ce712"},
    "linea:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E"},
    "scroll:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E"},
    "zksync:mainnet": {"factory": ""},
    "pzkevm:mainnet": {"factory": "0xd2002373543Ce3527023C75e7518C274A51ce712"},
    "mantle:mainnet": {"factory": ""},
    # Layer 1
    "gnosis:mainnet": {"factory": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8"},
    "polygon:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585"},
    "avax:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585"},
    "ftm:mainnet": {"factory": "0xe61Fb97Ef6eBFBa12B36Ffd7be785c1F5A2DE66b"},
    "bsc:mainnet": {"factory": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B"},
    "celo:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585"},
    "kava:mainnet": {"factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585"},
    "aurora:mainnet": {"factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E"},
    "tron:mainnet": {"factory": ""},
}


# -------------------------- POOL SETUP --------------------------


@dataclass
class PoolSettings:
    name: str
    symbol: str
    coins: List[Address]
    A: int
    fee: int
    offpeg_fee_multiplier: int
    ma_exp_time: int
    implementation_idx: int
    asset_types: List[int]
    method_ids: List[int]
    oracles: List[Address]


pool_settings = {
    "ethereum:mainnet": {
        "meta": [
            "0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # 3pool
            "USDV-3crv",  # name
            "USDV3crv",  # symbol
            "0x0E573Ce2736Dd9637A0b21058352e1667925C7a8",
            500,  # A
            1000000,  # fee
            50000000000,  # offpeg_fee_multiplier
            866,  # ma_exp_time
            0,  # implementation index
            0,  # asset_types
            b"",  # method_ids
            ZERO_ADDRESS,  # oracles
        ],
        "plain": [
            "FRAXsDAI",  # name
            "FRAXSDAI",  # symbol
            [
                "0x853d955aCEf822Db058eb8505911ED77F175b99e",  # frax
                "0x83F20F44975D03b1b09e64809B757c47f942BEeA",  # sdai
            ],
            1500,  # A
            1000000,  # fee
            10000000000,  # offpeg_fee_multiplier
            865,  # ma_exp_time
            0,  # implementation index
            [0, 3],  # asset_types
            [b"", b""],  # method_ids
            [ZERO_ADDRESS, ZERO_ADDRESS],  # oracles
        ],
    }
}


def deploy_pool(network, url, account, pool_type, fork):
    logger.log(f"Deploying pool on {network} ...")

    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
        boa.env.eoa = FIDDYDEPLOYER  # set eoa address here
    else:
        logger.log("Prodmode ...")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy")
    factory = factory.at(deployments[network]["factory"])

    logger.log("Deploying pool ...")
    args = pool_settings[network][pool_type]
    if pool_type == "plain":
        amm_address = factory.deploy_plain_pool(*args)
    elif pool_type == "meta":
        amm_address = factory.deploy_metapool(*args)

    logger.log(f"Deployed pool {amm_address}.")

    return amm_address


def deploy_gauge(network, url, account, pool_addr, fork):
    logger.log(f"Deploying gauge for pool {pool_addr} on {network} ...")

    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
        boa.env.eoa = FIDDYDEPLOYER  # set eoa address here
        assert boa.env.eoa  # EOA NOT SET!
    else:
        logger.log("Prodmode ...")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy")
    factory = factory.at(deployments[network]["factory"])

    logger.log("Deploying gauge ...")
    gauge_address = factory.deploy_gauge(pool_addr)

    logger.log(f"Deployed Gauge {gauge_address} for pool {pool_addr}.")


def deploy_pool_and_gauge(network, url, account, pool_type, fork):
    logger.log(f"Deploying pool on {network} ...")

    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
        boa.env.eoa = FIDDYDEPLOYER  # set eoa address here
    else:
        logger.log("Prodmode ...")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy")
    factory = factory.at(deployments[network]["factory"])

    logger.log("Deploying pool ...")
    args = pool_settings[network][pool_type]
    if pool_type == "plain":
        amm_address = factory.deploy_plain_pool(*args)
    elif pool_type == "meta":
        amm_address = factory.deploy_metapool(*args)

    logger.log(f"Deployed pool {amm_address}.")

    gauge_address = factory.deploy_gauge(amm_address)

    logger.log(f"Deployed Gauge {gauge_address} for pool {amm_address}.")


def main():
    fork = False
    deploy_pool_and_gauge("ethereum:mainnet", os.environ["RPC_ETHEREUM"], "FIDDYDEPLOYER", "plain", fork)
    deploy_pool_and_gauge("ethereum:mainnet", "http://localhost:9090/", "FIDDYDEPLOYER", "meta", fork)


if __name__ == "__main__":
    main()
