import os
import sys

import boa
import boa_zksync
import deployment_utils as deploy_utils
from boa.network import NetworkEnv
from eth_abi import encode
from eth_account import Account
from rich.console import Console as RichConsole

# sys.path.append(".")
from scripts import deployments

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

logger = RichConsole(file=sys.stdout)


def fetch_url(network):
    return os.getenv("DRPC_URL") % (network, os.getenv("DRPC_KEY"))


def set_contract_pragma(contract_file, network) -> boa.contracts.vyper.vyper_contract.VyperDeployer:
    with open(contract_file, "r") as f:
        source = f.read()

    is_shanghai_chain = any([x in network for x in ["ethereum", "gnosis"]])

    if is_shanghai_chain and "# pragma evm-version paris" in source:
        logger.log("Replacing EVM version to Shanghai ...")
        new_source = source.replace("# pragma evm-version paris\n", "# pragma evm-version shanghai\n")
    elif not is_shanghai_chain and "# pragma evm-version shanghai" in source:
        logger.log("Replacing EVM version to Paris ...")
        new_source = source.replace("# pragma evm-version shanghai\n", "# pragma evm-version paris\n")
    else:  # all looks good ...
        new_source = source

    is_zksync = "zksync" in network
    if is_zksync:
        logger.log("Cannot use compiler optimisations in zksync. Removing optimizer flags")
        if "# pragma optimize gas" in new_source:
            new_source = source.replace("# pragma optimize gas\n", "#\n")
        if "# pragma optimize codesize" in new_source:
            new_source = source.replace("# pragma optimize codesize\n", "#\n")

    contract_obj = boa.loads_partial(source_code=new_source, filename=contract_file)
    return contract_obj


def check_and_deploy(contract_obj, contract_designation, network, blueprint: bool = False, args=[]):
    deployed_contract = deployments.deployments[network][contract_designation]
    try:
        contract_name = os.path.basename(contract_obj.filename)
    except AttributeError:
        contract_name = os.path.basename(contract_obj._filename)

    if not deployed_contract:
        logger.log(f"Deploying {contract_designation} contract ...")
        if not blueprint:
            contract = contract_obj.deploy(*args)
            if args:
                constructor_args = encode(["address", "address"], args)
                logger.log(f"Constructor arguments for {contract_designation}: {constructor_args.hex()}")
        else:
            if "zksync:mainnet" in network:
                if "CurveStableSwapNG.vy" == contract_name:
                    contract = contract_obj.deploy_as_blueprint(
                        "blueprint",  # name
                        "BLUEPRINT",  # symbol
                        1500,  # A
                        1000000,  # fee
                        10000000000,  # offpeg_fee_multiplier
                        865,  # ma_exp_time
                        [
                            "0x1d17CBcF0D6D143135aE902365D2E5e2A16538D4",  # native usdc
                            "0x493257fD37EDB34451f62EDf8D2a0C418852bA4C",  # native usdt
                        ],
                        [10**18, 10**18],  # rate_multipliers
                        [0, 0],  # asset_types
                        [b"", b""],  # method_ids
                        [ZERO_ADDRESS, ZERO_ADDRESS],  # oracles
                    )

                elif "CurveStableSwapMetaNG.vy" == contract_name:
                    contract = contract_obj.deploy_as_blueprint(
                        "blueprint",  # name
                        "BLUEPRINT",  # symbol
                        500,  # A
                        1000000,  # fee
                        50000000000,  # offpeg_fee_multiplier
                        866,  # ma_exp_time
                        ZERO_ADDRESS,  # math_implementation
                        "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",  # base_pool (but we use bridged usdc)
                        ["0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4"],  # coins (bridged usdc)
                        [
                            "0x1d17CBcF0D6D143135aE902365D2E5e2A16538D4",  # native usdc
                            "0x493257fD37EDB34451f62EDf8D2a0C418852bA4C",  # native usdt
                        ],  # base coins
                        [10**18],  # rate_multipliers
                        [0],  # asset_types
                        [b""],  # method_ids
                        [ZERO_ADDRESS],  # oracles
                    )

            else:
                contract = contract_obj.deploy_as_blueprint()

        logger.log(f"Deployed! At: {contract.address}.")
    else:
        logger.log(f"Deployed {contract_designation} contract exists. Using {deployed_contract} ...")
        contract = contract_obj.at(deployed_contract)

    return contract


def deploy_infra(network, url, account, fork=False):
    logger.log(f"Deploying on {network} ...")

    if network == "zksync:mainnet":
        if not fork:
            boa_zksync.set_zksync_env(url)
            logger.log("Prodmode on zksync Era ...")
        else:
            boa_zksync.set_zksync_fork(url)
            logger.log("Forkmode on zksync Era ...")

        boa.env.set_eoa(Account.from_key(os.environ[account]))

    else:
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
            owner = data.dao_ownership_contract
            fee_receiver = data.fee_receiver_address

    assert owner, f"Curve's DAO contracts may not be on {network}."
    assert fee_receiver, f"Curve's DAO contracts may not be on {network}."

    # --------------------- Deploy math, views, blueprints ---------------------

    # get source and set evm_version
    math_contract_obj = set_contract_pragma("./contracts/main/CurveStableSwapNGMath.vy", network)
    views_contract_obj = set_contract_pragma("./contracts/main/CurveStableSwapNGViews.vy", network)
    plain_contract_obj = set_contract_pragma("./contracts/main/CurveStableSwapNG.vy", network)
    meta_contract_obj = set_contract_pragma("./contracts/main/CurveStableSwapMetaNG.vy", network)

    # deploy non-blueprint contracts:
    math_contract = check_and_deploy(math_contract_obj, "math", network)
    views_contract = check_and_deploy(views_contract_obj, "views", network)

    # deploy blueprints:
    plain_blueprint = check_and_deploy(plain_contract_obj, "plain_amm", network, blueprint=True)
    meta_blueprint = check_and_deploy(meta_contract_obj, "meta_amm", network, blueprint=True)

    # Factory:
    factory_contract_obj = set_contract_pragma("./contracts/main/CurveStableSwapFactoryNG.vy", network)
    args = [fee_receiver, deploy_utils.FIDDYDEPLOYER]
    factory = check_and_deploy(factory_contract_obj, "factory", network, False, args)

    # zap:
    zap_contract_obj = set_contract_pragma("./contracts/main/MetaZapNG.vy", network)
    check_and_deploy(zap_contract_obj, "zap", network)

    # Set up AMM implementations:÷
    current_views_impl = factory.views_implementation()
    if not current_views_impl == views_contract.address:
        logger.log(f"Current views implementation: {current_views_impl}")
        factory.set_views_implementation(views_contract.address)
        logger.log(f"Set views implementation to: {views_contract.address}")

    current_math_impl = factory.math_implementation()
    if not current_math_impl == math_contract.address:
        logger.log(f"Current math implementation: {current_math_impl}")
        factory.set_math_implementation(math_contract.address)
        logger.log(f"Set math implementation to: {math_contract.address}")

    current_pool_impl = factory.pool_implementations(0)
    if not current_pool_impl == plain_blueprint.address:
        logger.log(f"Current 'plain' pool impl at index 0: {current_pool_impl}")
        factory.set_pool_implementations(0, plain_blueprint.address)
        logger.log(f"Set plain amm implementation at index 0 to: {plain_blueprint.address}")

    current_metapool_impl = factory.metapool_implementations(0)
    if not current_metapool_impl == meta_blueprint.address:
        logger.log(f"Current metapool impl at index 0: {current_metapool_impl}")
        factory.set_metapool_implementations(0, meta_blueprint.address)
        logger.log(f"Set meta amm implementation to: {meta_blueprint.address}")

    if "ethereum" in network:  # Gauge contract only for Ethereum.
        logger.log("Deploying and setting up Gauge contracts ...")
        gauge_contract_obj = set_contract_pragma("./contracts/main/LiquidityGauge.vy", network)
        gauge_blueprint = check_and_deploy(gauge_contract_obj, "gauge", network, blueprint=True)

        if not factory.gauge_implementation() == gauge_blueprint.address:
            factory.set_gauge_implementation(gauge_blueprint.address)
            logger.log(f"Set liquidity gauge implementation to: {gauge_blueprint.address}")

    logger.log("Infra deployed!")


def main():
    deployer = "FIDDYDEPLOYER"
    fork = False
    network = "zksync"

    if network == "zksync":
        rpc = "https://mainnet.era.zksync.io"
    elif network == "fraxtal":
        rpc = "https://rpc.frax.com"
    elif network == "xlayer":
        rpc = "https://rpc.xlayer.tech"
    else:
        rpc = fetch_url(network)

    deploy_infra(f"{network}:mainnet", rpc, deployer, fork=fork)


if __name__ == "__main__":
    main()
