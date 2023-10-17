import os
import sys

import boa
from boa.network import NetworkEnv
from eth_account import Account
from rich.console import Console as RichConsole

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
        "ethereum:sepolia",
        "https://eth-sepolia.g.alchemy.com/v2/{alchemy_key}",
        "FIDDYDEPLOYER",
        "0x8a00365ae28d75b92ec695d5a041b744f140438d",
        False,  # forkmode
    )


if __name__ == "__main__":
    main()
