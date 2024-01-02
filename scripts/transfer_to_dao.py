import os
import sys

import boa
import deployment_utils as deploy_utils
from boa.network import NetworkEnv
from deploy_infra import deployments
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def transfer_ownership(network, url, account, fork=False):

    logger.log(f"Deploying on {network} ...")

    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
        boa.env.eoa = deploy_utils.FIDDYDEPLOYER  # set eoa address here
    else:
        logger.log("Prodmode ...")
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))

    for _network, data in deploy_utils.curve_dao_network_settings.items():

        if _network in network:

            curve_dao_ownership_agent = data.dao_ownership_contract
            factory = boa.load_partial("contracts/main/CurveStableSwapFactoryNG.vy").at(deployments[network]["factory"])

    current_factory_admin = factory.admin()
    assert boa.env.eoa == current_factory_admin
    assert curve_dao_ownership_agent != current_factory_admin

    factory.commit_transfer_ownership(curve_dao_ownership_agent)

    assert factory.future_admin() == curve_dao_ownership_agent
    logger.log(
        f"Committed Ownership transfer of Factory {factory.address} in network {network} "
        f"from {current_factory_admin} to {curve_dao_ownership_agent}."
    )

    if fork:

        with boa.reverts():
            factory.accept_transfer_ownership(sender=current_factory_admin)

        factory.accept_transfer_ownership(sender=curve_dao_ownership_agent)

        # as a test, add an asset type in forkmode only:
        factory.add_asset_type(9, "TEST", sender=curve_dao_ownership_agent)
        logger.log("Successfully transferred ownership!")


def main():

    forkmode = False

    transfer_ownership(
        "base:mainnet",
        os.environ["RPC_BASE"],
        "FIDDYDEPLOYER",
        fork=forkmode,
    )


if __name__ == "__main__":
    main()
