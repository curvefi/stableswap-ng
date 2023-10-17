import os
import sys

import boa
from boa.network import NetworkEnv
from deploy_infra import deployments
from deployment_utils import pool_settings
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def deploy_pool(network, url, account, fork, pool_type):

    if fork:
        boa.env.fork(url)
    else:
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy")
    factory = factory.at(deployments["gnosis:mainnet"]["factory"])

    logger.log("Deploying pool ...")
    args = pool_settings[network][pool_type]
    if pool_type == "plain":
        amm_address = factory.deploy_plain_pool(*args)
    elif pool_type == "meta":
        amm_address = factory.deploy_metapool(*args)

    logger.log(f"Deployed Plain pool {amm_address}.")


def main():
    deploy_pool("gnosis:mainnet", "https://gnosis.drpc.org", "FIDDYDEPLOYER", False, "meta")  # forkmode


if __name__ == "__main__":
    main()
