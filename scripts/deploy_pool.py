import os
import sys

import boa
from boa.network import NetworkEnv
from deploy_infra import deployments
from deployment_utils import pool_settings
from eth_abi import encode
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def deploy_plain_pool(network, url, account, fork=False):

    if fork:
        boa.env.fork(url)
    else:
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    factory = boa.load_partial("./contracts/main/CurveStableSwapFactoryNG.vy")
    factory = factory.at(deployments["gnosis:mainnet"]["factory"])

    args = pool_settings[network]["plain"]
    call_sig = [
        "string",
        "string",
        "address[]",
        "uint256",
        "uint256",
        "uint256",
        "uint256",
        "uint256",
        "uint8[]",
        "bytes4[]",
        "address[]",
    ]
    encoded_args = encode(call_sig, args)
    print(f"Encoded args: {encoded_args.hex()}")
    logger.log("Deploying pool ...")
    amm_address = factory.deploy_plain_pool(*args)
    logger.log(f"Deployed Plain pool {amm_address}.")


def main():
    deploy_plain_pool(
        "gnosis:mainnet",
        "https://gnosis.drpc.org",
        "FIDDYDEPLOYER",
        False,  # forkmode
    )


if __name__ == "__main__":
    main()
