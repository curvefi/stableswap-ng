import os
import sys

import boa
from boa.network import NetworkEnv
from eth_account import Account
from rich.console import Console as RichConsole

from scripts.deploy_infra import deployments

logger = RichConsole(file=sys.stdout)


def deploy_plain_pool(network, url, account, factory, fork=False):

    if fork:
        boa.env.fork(url)
    else:
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy").at(factory)


def main():
    deploy_plain_pool(
        "gnosis:mainnet",
        "https://gnosis.drpc.org",
        "FIDDYDEPLOYER",
        deployments["gnosis:mainnet"]["factory"],
        False,  # forkmode
    )


if __name__ == "__main__":
    main()
