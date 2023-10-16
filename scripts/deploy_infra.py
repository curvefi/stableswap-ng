import os
import sys

import boa
import deployment_utils as deploy_utils
from boa.network import NetworkEnv
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)


def set_evm_version(contract_file, network) -> boa.vyper.contract.VyperDeployer:

    with open(contract_file, "r") as f:
        source = f.read()

    if "ethereum" in network and "# pragma evm-version paris" in source:
        source.replace("# pragma evm-version paris", "# pragma evm-version shanghai")
    elif "ethereum" not in network and "# pragma evm-version shanghai" in source:
        source.replace("# pragma evm-version shanghai", "# pragma evm-version paris")

    return boa.loads_partial(source_code=source)


def deploy_infra(network, url, account, fork=False):

    if fork:
        boa.env.fork(url)
    else:
        boa.set_env(NetworkEnv(url))
        boa.env.add_account(Account.from_key(os.environ[account]))
    for _network, data in deploy_utils.curve_dao_network_settings.items():

        if _network in network:

            owner = data.dao_ownership_contract
            fee_receiver = data.fee_receiver_address

    assert owner, f"Curve's DAO contracts may not be on {network}."
    assert fee_receiver, f"Curve's DAO contracts may not be on {network}."

    # --------------------- Deploy math, views, blueprints ---------------------

    logger.log("Setting EVM versions ...")

    # get source and set evm_version
    math_contract_obj = set_evm_version("./contracts/main/CurveStableSwapNGMath.vy", network)
    views_contract_obj = set_evm_version("./contracts/main/CurveStableSwapNGViews.vy", network)
    plain_contract_obj = set_evm_version("./contracts/main/CurveStableSwapNG.vy", network)
    meta_contract_obj = set_evm_version("./contracts/main/CurveStableSwapMetaNG.vy", network)
    gauge_contract_obj = set_evm_version("./contracts/main/LiquidityGauge.vy", network)

    # deploy non-blueprint contracts:
    logger.log("Deploying non-blueprint AMM components ...")
    math_contract = math_contract_obj.deploy()
    views_contract = views_contract_obj.deploy()

    # deploy blueprints:
    logger.log("Deploying blueprints ...")
    plain_blueprint = plain_contract_obj.deploy_as_blueprint()
    meta_blueprint = meta_contract_obj.deploy_as_blueprint()
    gauge_blueprint = gauge_contract_obj.deploy_as_blueprint()

    # Factory:
    factory_contract_obj = set_evm_version("./contracts/main/CurveStableSwapFactoryNG.vy", network)
    logger.log("Deploying factory ...")
    factory = factory_contract_obj.deploy(fee_receiver, deploy_utils.FIDDYDEPLOYER)

    # Set it all up:
    logger.log("Integrating AMM components into factory ...")
    factory.set_gauge_implementation(gauge_blueprint.address)
    factory.set_views_implementation(views_contract.address)
    factory.set_math_implementation(math_contract.address)
    factory.set_pool_implementations(0, plain_blueprint.address)
    factory.set_metapool_implementations(0, meta_blueprint.address)


def main():
    deploy_infra(
        "ethereum:sepolia",
        "https://eth-sepolia.g.alchemy.com/v2/{alchemy_key}",
        "FIDDYDEPLOYER",
        False,  # forkmode
    )


if __name__ == "__main__":
    main()
