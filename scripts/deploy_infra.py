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
    # Ethereum
    "ethereum:mainnet": {
        "math": "0xc9CBC565A9F4120a2740ec6f64CC24AeB2bB3E5E",
        "views": "0xe0B15824862f3222fdFeD99FeBD0f7e0EC26E1FA",
        "plain_amm": "0xDCc91f930b42619377C200BA05b7513f2958b202",
        "meta_amm": "0xede71F77d7c900dCA5892720E76316C6E575F0F7",
        "factory": "0x6A8cbed756804B16E05E741eDaBd5cB544AE21bf",
        "gauge": "0x38D9BdA812da2C68dFC6aDE85A7F7a54E77F8325",
    },
    "ethereum:sepolia": {
        "math": "0x2cad7b3e78e10bcbf2cc443ddd69ca8bcc09a758",
        "views": "0x9d3975070768580f755D405527862ee126d0eA08",
        "plain_amm": "0xE12374F193f91f71CE40D53E0db102eBaA9098D5",
        "meta_amm": "0xB00E89EaBD59cD3254c88E390103Cf17E914f678",
        "factory": "0xfb37b8D939FFa77114005e61CFc2e543d6F49A81",
    },
    # Layer 2
    "arbitrum:mainnet": {
        "math": "0xD4a8bd4d59d65869E99f20b642023a5015619B34",
        "views": "0x9293f068912bae932843a1bA01806c54f416019D",
        "plain_amm": "0xf6841C27fe35ED7069189aFD5b81513578AFD7FF",
        "meta_amm": "0xFf02cBD91F57A778Bab7218DA562594a680B8B61",
        "factory": "0x9AF14D26075f142eb3F292D5065EB3faa646167b",
    },
    "optimism:mainnet": {
        "math": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "views": "0xf3A6aa40cf048a3960E9664847E9a7be025a390a",
        "plain_amm": "0x635742dCC8313DCf8c904206037d962c042EAfBd",
        "meta_amm": "0x5702BDB1Ec244704E3cBBaAE11a0275aE5b07499",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
    },
    "base:mainnet": {
        "math": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "views": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "plain_amm": "0xf3A6aa40cf048a3960E9664847E9a7be025a390a",
        "meta_amm": "0x635742dCC8313DCf8c904206037d962c042EAfBd",
        "factory": "0xd2002373543Ce3527023C75e7518C274A51ce712",
    },
    "linea:mainnet": {
        "math": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "views": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "plain_amm": "0xa7b9d886a9a374a1c86dc52d2ba585c5cdfdac26",
        "meta_amm": "0xf3a6aa40cf048a3960e9664847e9a7be025a390a",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
    },
    "scroll:mainnet": {
        "math": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "views": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "plain_amm": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "meta_amm": "0xf3A6aa40cf048a3960E9664847E9a7be025a390a",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
    },
    "pzkevm:mainnet": {
        "math": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "views": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "plain_amm": "0xf3A6aa40cf048a3960E9664847E9a7be025a390a",
        "meta_amm": "0x635742dCC8313DCf8c904206037d962c042EAfBd",
        "factory": "0xd2002373543Ce3527023C75e7518C274A51ce712",
    },
    # Layer 1
    "gnosis:mainnet": {
        "math": "0xFAbC421e3368D158d802684A217a83c083c94CeB",
        "views": "0x0c59d36b23f809f8b6C7cb4c8C590a0AC103baEf",
        "plain_amm": "0x3d6cb2f6dcf47cdd9c13e4e3beae9af041d8796a",
        "meta_amm": "0xC1b393EfEF38140662b91441C6710Aa704973228",
        "factory": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
    },
    "polygon:mainnet": {
        "math": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",
        "views": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "plain_amm": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "meta_amm": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "avax:mainnet": {
        "math": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",
        "views": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "plain_amm": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "meta_amm": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "ftm:mainnet": {
        "math": "0xf3A6aa40cf048a3960E9664847E9a7be025a390a",
        "views": "0x635742dCC8313DCf8c904206037d962c042EAfBd",
        "plain_amm": "0x5702BDB1Ec244704E3cBBaAE11a0275aE5b07499",
        "meta_amm": "0x046207cB759F527b6c10C2D61DBaca45513685CC",
        "factory": "0xe61Fb97Ef6eBFBa12B36Ffd7be785c1F5A2DE66b",
    },
    "bsc:mainnet": {
        "math": "0x166c4084Ad2434E8F2425C64dabFE6875A0D45c5",
        "views": "0x5Ea9DD3b6f042A34Df818C6c1324BC5A7c61427a",
        "plain_amm": "0x505d666E4DD174DcDD7FA090ed95554486d2Be44",
        "meta_amm": "0x5a8C93EE12a8Df4455BA111647AdA41f29D5CfcC",
        "factory": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",
    },
    "celo:mainnet": {
        "math": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",
        "views": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "plain_amm": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "meta_amm": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "kava:mainnet": {
        "math": "0xd7E72f3615aa65b92A4DBdC211E296a35512988B",
        "views": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "plain_amm": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "meta_amm": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "factory": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
    },
    "aurora:mainnet": {
        "math": "0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8",
        "views": "0xe265FC390E9129b7E337Da23cD42E00C34Da2CE3",
        "plain_amm": "0xa7b9d886A9a374A1C86DC52d2BA585c5CDFdac26",
        "meta_amm": "0xf3A6aa40cf048a3960E9664847E9a7be025a390a",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
    },
    "mantle:mainnet": {
        "math": "0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6",
        "views": "0x506F594ceb4E33F5161139bAe3Ee911014df9f7f",
        "plain_amm": "0x87FE17697D0f14A222e8bEf386a0860eCffDD617",
        "meta_amm": "0x1764ee18e8B3ccA4787249Ceb249356192594585",
        "factory": "0x5eeE3091f747E60a045a2E715a4c71e600e31F6E",
        "factory_ctor": "000000000000000000000000f3a431008396df8a8b2df492c913706bdb0874ef0000000000000000000000002d12d0907a388811e3aa855a550f959501d303ee",  # noqa:E501
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
    deploy_infra("ethereum:mainnet", os.environ["RPC_ETHEREUM"], "FIDDYDEPLOYER", fork=False)


if __name__ == "__main__":
    main()
