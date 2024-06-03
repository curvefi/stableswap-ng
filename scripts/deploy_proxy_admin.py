import os
import sys

import boa
import boa_zksync
from boa.network import NetworkEnv
from deploy_infra import set_contract_pragma
from deployment_utils import BABE, FIDDYDEPLOYER
from eth_abi import encode
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def deploy_proxy_admin(network, url, account, fork=False):
    logger.log(f"Deploying ProxyAdmin for {network} ...")

    if network == "zksync":
        assert not fork
        boa_zksync.set_zksync_env(url)
        logger.log("Prodmode on zksync Era ...")
        boa.env.add_account(Account.from_key(os.environ[account]))

    else:
        if fork:
            boa.env.fork(url)
            logger.log("Forkmode ...")
            boa.env.eoa = FIDDYDEPLOYER
        else:
            logger.log("Prodmode ...")
            boa.set_env(NetworkEnv(url))
            boa.env.add_account(Account.from_key(os.environ[account]))

    # deploy thin proxy if no owners exist:
    proxy_admin_contract_obj = set_contract_pragma("./contracts/ProxyAdmin.vy", network)
    args = [FIDDYDEPLOYER, BABE]
    encoded_args = encode(["address", "address"], args).hex()
    logger.log(f"Constructor: {encoded_args}")
    proxy_admin = proxy_admin_contract_obj.deploy(args)
    logger.log(f"Deployed ProxyAdmin at {proxy_admin.address} on {network}.")


def main():
    network = "zksync"
    rpc = "https://mainnet.era.zksync.io"
    account = "FIDDYDEPLOYER"
    fork = False
    deploy_proxy_admin(network, rpc, account, fork)


if __name__ == "__main__":
    main()
