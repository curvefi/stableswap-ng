import os
import sys
from dataclasses import dataclass
from typing import List

import boa
from boa.network import NetworkEnv
from deploy_infra import deployments
from deployment_utils import FIDDYDEPLOYER
from eth_account import Account
from eth_typing import Address
from eth_utils import to_checksum_address
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


# ------------- BASE POOLS ---------------


@dataclass
class BasePoolSettings:
    pool: Address
    lp_token: Address
    coins: List[Address]
    asset_types: List[int]
    n_coins: int


base_pool_list = {
    "ethereum:mainnet": [
        BasePoolSettings(  # 3pool
            pool="0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",
            lp_token="0x6c3F90f043a72FA612cbac8115EE7e52BDe6E490",
            coins=[
                "0x6B175474E89094C44Da98b954EedeAC495271d0F",  # dai
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # usdc
                "0xdAC17F958D2ee523a2206206994597C13D831ec7",  # usdt
            ],
            asset_types=[0, 0, 0],
            n_coins=3,
        ),
        BasePoolSettings(  # fraxusdc
            pool="0xDcEF968d416a41Cdac0ED8702fAC8128A64241A2",
            lp_token="0x3175Df0976dFA876431C2E9eE6Bc45b65d3473CC",
            coins=[
                "0x853d955aCEf822Db058eb8505911ED77F175b99e",  # frax
                "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",  # usdc
            ],
            asset_types=[0, 0],
            n_coins=2,
        ),
        BasePoolSettings(  # sbtc/wbtc
            pool="0xf253f83AcA21aAbD2A20553AE0BF7F65C755A07F",
            lp_token="0x051d7e5609917Bd9b73f04BAc0DED8Dd46a74301",
            coins=[
                "0xfE18be6b3Bd88A2D2A7f928d00292E7a9963CfC6",  # sbtc
                "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599",  # wbtc
            ],
            asset_types=[0, 0],
            n_coins=2,
        ),
        BasePoolSettings(
            pool="0xaE34574AC03A15cd58A92DC79De7B1A0800F1CE3",
            lp_token="0xFC2838a17D8e8B1D5456E0a351B0708a09211147",
            coins=[
                "0x853d955aCEf822Db058eb8505911ED77F175b99e",  # frax
                "0x8E870D67F660D95d5be530380D0eC0bd388289E1",  # usdp
            ],
            asset_types=[0, 0],
            n_coins=2,
        ),
    ],
    "arbitrum:mainnet": [
        BasePoolSettings(  # 2pool
            pool="0x7f90122BF0700F9E7e1F688fe926940E8839F353",
            lp_token="0x7f90122BF0700F9E7e1F688fe926940E8839F353",
            coins=[
                "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
                "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
            ],
            asset_types=[0, 0],
            n_coins=2,
        ),
        BasePoolSettings(  # fraxbp
            pool="0xC9B8a3FDECB9D5b218d02555a8Baf332E5B740d5",
            lp_token="0xC9B8a3FDECB9D5b218d02555a8Baf332E5B740d5",
            coins=[
                "0x17FC002b466eEc40DaE837Fc4bE5c67993ddBd6F",
                "0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8",
            ],
            asset_types=[0, 0],
            n_coins=2,
        ),
    ],
    "optimism:mainnet": [
        BasePoolSettings(  # 3pool
            pool="0x1337BedC9D22ecbe766dF105c9623922A27963EC",
            lp_token="0x1337BedC9D22ecbe766dF105c9623922A27963EC",
            coins=[
                "0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
                "0x94b008aA00579c1307B0EF2c499aD98a8ce58e58",
            ],
            asset_types=[0, 0, 0],
            n_coins=3,
        ),
        BasePoolSettings(  # fraxbp
            pool="0x29A3d66B30Bc4AD674A4FDAF27578B64f6afbFe7",
            lp_token="0x29A3d66B30Bc4AD674A4FDAF27578B64f6afbFe7",
            coins=[
                "0x2E3D870790dC77A83DD1d18184Acc7439A53f475",
                "0x7F5c764cBc14f9669B88837ca1490cCa17c31607",
            ],
            asset_types=[0, 0],
            n_coins=2,
        ),
    ],
    "gnosis:mainnet": [
        BasePoolSettings(
            pool="0x7f90122bf0700f9e7e1f688fe926940e8839f353",
            lp_token="0x1337BedC9D22ecbe766dF105c9623922A27963EC",
            coins=[
                "0xe91D153E0b41518A2Ce8Dd3D7944Fa863463a97d",
                "0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83",
                "0x4ECaBa5870353805a9F068101A40E0f32ed605C6",
            ],
            asset_types=[0, 0, 0],
            n_coins=3,
        )
    ],
}


def set_up_base_pools(network, url, account, fork: bool = False):
    logger.log(f"Connecting to {network} ...")
    if fork:
        boa.env.fork(url)
        boa.env.eoa = FIDDYDEPLOYER
        logger.log("Forkmode")
    else:
        logger.log("Prodmode")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory_address = deployments[network]["factory"]
    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy").at(factory_address)

    logger.log("Setting up base pools ...")
    base_pool_data = base_pool_list[network]
    onboarded_base_pools = [factory.base_pool_list(i) for i in range(factory.base_pool_count())]

    if base_pool_data:  # check if network has base pools:
        for data in base_pool_data:
            if to_checksum_address(data.pool) not in onboarded_base_pools:
                factory.add_base_pool(data.pool, data.lp_token, data.asset_types, data.n_coins)
                logger.log(f"Added {data.pool} to factory {factory_address} on {network}.")
            else:
                logger.log(
                    f"{data.pool} is already configured as a base pool in factory {factory_address}."
                )

            assert factory.base_pool_data(data.pool)[0] == data.lp_token

    logger.log(f"Base pools set up for {network}!")


def main():
    fork = False

    set_up_base_pools("ethereum:mainnet", os.environ["RPC_ETHEREUM"], "FIDDYDEPLOYER", fork=fork)
    set_up_base_pools("arbitrum:mainnet", os.environ["RPC_ARBITRUM"], "FIDDYDEPLOYER", fork=fork)
    set_up_base_pools("optimism:mainnet", os.environ["RPC_OPTIMISM"], "FIDDYDEPLOYER", fork=fork)
    set_up_base_pools("gnosis:mainnet", os.environ["RPC_GNOSIS"], "FIDDYDEPLOYER", fork=fork)


if __name__ == "__main__":
    main()
