import os
import sys

import boa
import deployment_utils as deploy_utils
from boa.network import NetworkEnv
from eth_abi import encode
from eth_account import Account
from rich.console import Console as RichConsole

logger = RichConsole(file=sys.stdout)

deployments = {
    "ethereum:sepolia": {
        "math": "0xbc7654d2dd901aaaa3be4cb5bc0f10dea9f96443",
        "views": "0x07920e98a66e462c2aa4c8fa6200bc68ca161ea0",
        "plain_amm": "0x296d2b5c23833a70d07c8fcbb97d846c1ff90ddd",
        "meta_amm": "0xdd7ebb1c49780519dd9755b8b1a23a6f42ce099e",
        "gauge": "0x64891ab20392a029c0f231656ff13c5ee64b730c",
        "factory": "0x8a00365ae28d75b92ec695d5a041b744f140438d",
    },
    "gnosis:mainnet": {
        "math": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "views": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
        "plain_amm": "0xd2002373543Ce3527023C75e7518C274A51ce712",
        "meta_amm": "0x686bdb3D24Bc6F3ED89ed3d3B659765c54aC78B4",
        "factory": "0xe61Fb97Ef6eBFBa12B36Ffd7be785c1F5A2DE66b",
    },
}


def set_evm_version(contract_file, network) -> boa.vyper.contract.VyperDeployer:

    with open(contract_file, "r") as f:
        source = f.read()

    is_shanghai_chain = any([x in network for x in ["ethereum", "gnosis"]])

    if is_shanghai_chain and "# pragma evm-version paris" in source:
        logger.log("Replacing EVM version to Shanghai ...")
        source = source.replace("# pragma evm-version paris\n", "# pragma evm-version shanghai\n")
    elif not is_shanghai_chain and "# pragma evm-version shanghai" in source:
        logger.log("Replacing EVM version to Paris ...")
        source = source.replace("# pragma evm-version shanghai\n", "# pragma evm-version paris\n")

    return boa.loads_partial(source_code=source)


def check_and_deploy(contract_obj, contract_designation, network, blueprint: bool = False, args=[]):

    deployed_contract = deployments[network][contract_designation]

    if not deployed_contract:
        logger.log(f"Deploying {contract_designation} contract ...")
        if not blueprint:
            contract = contract_obj.deploy(*args)
        else:
            contract = contract_obj.deploy_as_blueprint()
        logger.log(f"Deployed! At: {contract.address}.")
    else:
        logger.log(f"Deployed {contract_designation} contract exists. Using {deployed_contract} ...")
        contract = contract_obj.at(deployed_contract)

    return contract


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

    # deploy non-blueprint contracts:
    logger.log("Deploying non-blueprint AMM components ...")
    math_contract = check_and_deploy(math_contract_obj, "math", network)
    views_contract = check_and_deploy(views_contract_obj, "views", network)

    # deploy blueprints:
    logger.log("Deploying blueprints ...")
    plain_blueprint = check_and_deploy(plain_contract_obj, "plain_amm", network, blueprint=True)
    meta_blueprint = check_and_deploy(meta_contract_obj, "meta_amm", network, blueprint=True)

    # Factory:
    factory_contract_obj = set_evm_version("./contracts/main/CurveStableSwapFactoryNG.vy", network)
    logger.log("Deploying factory ...")
    args = [fee_receiver, deploy_utils.FIDDYDEPLOYER]
    factory = check_and_deploy(factory_contract_obj, "factory", network, False, args)

    constructor_args = encode(["address", "address"], args)
    logger.log(f"Constructor arguments for factory: {constructor_args.hex()}")

    # Set up AMM implementations:
    logger.log("Integrating AMM components into factory ...")

    if not factory.views_implementation() == views_contract.address:
        factory.set_views_implementation(views_contract.address)
        logger.log(f"Set views implementation to: {views_contract.address}")

    if not factory.math_implementation() == math_contract.address:
        factory.set_math_implementation(math_contract.address)
        logger.log(f"Set math implementation to: {math_contract.address}")

    if not factory.pool_implementations(0) == plain_blueprint.address:
        factory.set_pool_implementations(0, plain_blueprint.address)
        logger.log(f"Set plain amm implementation to: {plain_blueprint.address}")

    if not factory.metapool_implementations(0) == meta_blueprint.address:
        factory.set_metapool_implementations(0, meta_blueprint.address)
        logger.log(f"Set meta amm implementation to: {meta_blueprint.address}")

    if "ethereum" in network:  # Gauge contract only for Ethereum.
        logger.log("Deploying and setting up Gauge contracts ...")
        gauge_contract_obj = set_evm_version("./contracts/main/LiquidityGauge.vy", network)
        gauge_blueprint = check_and_deploy(gauge_contract_obj, "gauge", network, blueprint=True)

        if not factory.gauge_implementation() == gauge_blueprint.address:
            factory.set_gauge_implementation(gauge_blueprint.address)
            logger.log(f"Set liquidity gauge implementation to: {gauge_blueprint.address}")

    logger.log("Infra deployed!")


def main():
    deploy_infra(
        "gnosis:mainnet",
        "https://gnosis.api.onfinality.io/public",
        "FIDDYDEPLOYER",
        False,  # forkmode
    )


if __name__ == "__main__":
    main()
