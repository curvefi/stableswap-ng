import os
import sys

import boa
from boa.network import NetworkEnv
from deploy_infra import deployments
from deployment_utils import base_pool_list
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def set_up_base_pools(network, url, account, factory, fork: bool = False):

    if fork:
        boa.env.fork(url)
    else:
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy").at(factory)

    logger.log("Setting up base pools ...")
    base_pool_data = base_pool_list[network]
    onboarded_base_pools = [factory.base_pool_list(i) for i in range(factory.base_pool_count())]

    if base_pool_data:  # check if network has base pools:
        for data in base_pool_data:
            if data.pool not in onboarded_base_pools:
                factory.add_base_pool(
                    data.pool,
                    data.lp_token,
                    data.asset_types,
                    data.n_coins,
                )
                logger.log(f"Added {data.pool} to factory {factory.address} on {network}.")

            assert factory.base_pool_data(data.pool)[0] == data.pool


def main():
    set_up_base_pools(
        "gnosis:mainnet",
        "https://gnosis.drpc.org",
        "FIDDYDEPLOYER",
        deployments["gnosis:mainnet"]["factory"],
        False,  # forkmode
    )


if __name__ == "__main__":
    main()
