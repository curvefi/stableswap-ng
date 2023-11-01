import os
import sys

import boa
import deployment_utils as deploy_utils
from boa.network import NetworkEnv
from deploy_infra import set_evm_version
from eth_abi import encode
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def deploy_proxy_admin(network, url, account, fork=False):

    logger.log(f"Deploying ProxyAdmin for {network} ...")

    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
        boa.env.eoa = deploy_utils.FIDDYDEPLOYER
    else:
        logger.log("Prodmode ...")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    # deploy thin proxy if no owners exist:
    proxy_admin_contract_obj = set_evm_version("./contracts/ProxyAdmin.vy", network)
    args = [deploy_utils.FIDDYDEPLOYER, deploy_utils.BABE]
    encoded_args = encode(["address", "address"], args).hex()
    logger.log(f"Constructor: {encoded_args}")
    proxy_admin = proxy_admin_contract_obj.deploy(args)
    logger.log(f"Deployed ProxyAdmin at {proxy_admin.address} on {network}.")


def main():
    deploy_proxy_admin(
        "mantle:mainnet",
        os.environ["RPC_MANTLE"],
        "FIDDYDEPLOYER",
        fork=True,
    )


if __name__ == "__main__":
    main()
