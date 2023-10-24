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
        "meta_amm": "0xa12A87c73718a34CD8601b5022B2C6C359142585",
        "gauge": "0x64891ab20392a029c0f231656ff13c5ee64b730c",
        "factory": "0xfb37b8D939FFa77114005e61CFc2e543d6F49A81",
    },
    "gnosis:mainnet": {
        "math": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "views": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
        "plain_amm": "0xd2002373543Ce3527023C75e7518C274A51ce712",
        "meta_amm": "0xd3B17f862956464ae4403cCF829CE69199856e1e",
        "factory": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
    },
    "arbitrum:mainnet": {
        "math": "0x3d6cB2F6DcF47CDd9C13E4e3beAe9af041d8796a",
        "views": "0xC1b393EfEF38140662b91441C6710Aa704973228",
        "plain_amm": "0x76303e4fDcA0AbF28aB3ee42Ce086E6503431F1D",
        "meta_amm": "0xd125E7a0cEddF89c6473412d85835450897be6Dc",
        "factory": "0x9AF14D26075f142eb3F292D5065EB3faa646167b",
    },
    "optimism:mainnet": {
        "math": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "views": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "plain_amm": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "meta_amm": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
    },
    "polygon:mainnet": {
        "math": "0xf3A431008396df8A8b2DF492C913706BDB0874ef",
        "views": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "plain_amm": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "meta_amm": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "base:mainnet": {
        "math": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "views": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "plain_amm": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
        "meta_amm": "0x5eee3091f747e60a045a2e715a4c71e600e31f6e",
        "factory": "0xd2002373543Ce3527023C75e7518C274A51ce712",
    },
    "avax:mainnet": {
        "math": "0xf3A431008396df8A8b2DF492C913706BDB0874ef",
        "views": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "plain_amm": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "meta_amm": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "ftm:mainnet": {
        "math": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "views": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
        "plain_amm": "0xd2002373543Ce3527023C75e7518C274A51ce712",
        "meta_amm": "0x686bdb3D24Bc6F3ED89ed3d3B659765c54aC78B4",
        "factory": "0xe61Fb97Ef6eBFBa12B36Ffd7be785c1F5A2DE66b",
    },
    "kava:mainnet": {
        "math": "",
        "views": "",
        "plain_amm": "",
        "meta_amm": "",
        "factory": "",
    },
    "celo:mainnet": {
        "math": "0xf3A431008396df8A8b2DF492C913706BDB0874ef",
        "views": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "plain_amm": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "meta_amm": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "aurora:mainnet": {
        "math": "",
        "views": "",
        "plain_amm": "",
        "meta_amm": "",
        "factory": "",
    },
    "bsc:mainnet": {
        "math": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "views": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
        "plain_amm": "0x604388Bb1159AFd21eB5191cE22b4DeCdEE2Ae22",
        "meta_amm": "0x06452f9c013fc37169B57Eab8F50A7A48c9198A3",
        "factory": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",
    },
    "linea:mainnet": {
        "math": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "views": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "plain_amm": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "meta_amm": "0x1764ee18e8b3cca4787249ceb249356192594585",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
    },
    "scroll:mainnet": {
        "math": "",
        "views": "",
        "plain_amm": "",
        "meta_amm": "",
        "factory": "",
    },
    "zksync:mainnet": {
        "math": "",
        "views": "",
        "plain_amm": "",
        "meta_amm": "",
        "factory": "",
    },
    "pzkevm:mainnet": {
        "math": "",
        "views": "",
        "plain_amm": "",
        "meta_amm": "",
        "factory": "",
    },
}


def set_evm_version(contract_file, network) -> boa.vyper.contract.VyperDeployer:

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

    contract_obj = boa.loads_partial(source_code=new_source)
    return contract_obj


def check_and_deploy(contract_obj, contract_designation, network, blueprint: bool = False, args=[]):

    deployed_contract = deployments[network][contract_designation]

    if not deployed_contract:
        logger.log(f"Deploying {contract_designation} contract ...")
        if not blueprint:
            contract = contract_obj.deploy(*args)
            if args:
                constructor_args = encode(["address", "address"], args)
                logger.log(f"Constructor arguments for {contract_designation}: {constructor_args.hex()}")
        else:
            contract = contract_obj.deploy_as_blueprint()
        logger.log(f"Deployed! At: {contract.address}.")
    else:
        logger.log(f"Deployed {contract_designation} contract exists. Using {deployed_contract} ...")
        contract = contract_obj.at(deployed_contract)

    return contract


def deploy_infra(network, url, account, fork=False):

    logger.log(f"Deploying on {network} ...")

    if fork:
        boa.env.fork(url)
        logger.log("Forkmode ...")
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
    math_contract_obj = set_evm_version("./contracts/main/CurveStableSwapNGMath.vy", network)
    views_contract_obj = set_evm_version("./contracts/main/CurveStableSwapNGViews.vy", network)
    plain_contract_obj = set_evm_version("./contracts/main/CurveStableSwapNG.vy", network)
    meta_contract_obj = set_evm_version("./contracts/main/CurveStableSwapMetaNG.vy", network)

    # deploy non-blueprint contracts:
    math_contract = check_and_deploy(math_contract_obj, "math", network)
    views_contract = check_and_deploy(views_contract_obj, "views", network)

    # deploy blueprints:
    plain_blueprint = check_and_deploy(plain_contract_obj, "plain_amm", network, blueprint=True)
    meta_blueprint = check_and_deploy(meta_contract_obj, "meta_amm", network, blueprint=True)

    # Factory:
    factory_contract_obj = set_evm_version("./contracts/main/CurveStableSwapFactoryNG.vy", network)
    args = [fee_receiver, deploy_utils.FIDDYDEPLOYER]
    factory = check_and_deploy(factory_contract_obj, "factory", network, False, args)

    # Set up AMM implementations:
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

    # # gnosis
    # deploy_infra(
    #     "gnosis:mainnet",
    #     os.environ["RPC_GNOSIS"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # ethereum sepolia
    # deploy_infra(
    #     "ethereum:sepolia",
    #     os.environ["RPC_ETHEREUM_SEPOLIA"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # arbitrum
    # deploy_infra(
    #     "arbitrum:mainnet",
    #     os.environ["RPC_ARBITRUM"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # optimism
    # deploy_infra(
    #     "optimism:mainnet",
    #     os.environ["RPC_OPTIMISM"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # polygon
    # deploy_infra(
    #     "polygon:mainnet",
    #     os.environ["RPC_POLYGON"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # base
    # deploy_infra(
    #     "base:mainnet",
    #     os.environ["RPC_BASE"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # avax
    # deploy_infra(
    #     "avax:mainnet",
    #     os.environ["RPC_AVAX"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # fantom
    # deploy_infra(
    #     "ftm:mainnet",
    #     os.environ["RPC_FANTOM"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # kava
    # deploy_infra(
    #     "kava:mainnet",
    #     os.environ["RPC_KAVA"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # celo
    # deploy_infra(
    #     "celo:mainnet",
    #     os.environ["RPC_CELO"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # aurora
    # deploy_infra(
    #     "aurora:mainnet",
    #     os.environ["RPC_AURORA"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # bsc
    # deploy_infra(
    #     "bsc:mainnet",
    #     os.environ["RPC_BSC"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )

    # # linea
    deploy_infra(
        "linea:mainnet",
        os.environ["RPC_LINEA"],
        "FIDDYDEPLOYER",
        fork=False,
    )

    # # eth
    # deploy_infra(
    #     "ethereum:mainnet",
    #     os.environ["RPC_ETHEREUM"],
    #     "FIDDYDEPLOYER",
    #     fork=False,
    # )


if __name__ == "__main__":
    main()
