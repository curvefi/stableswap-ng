import click
from ape import Contract, accounts, project
from ape.cli import NetworkBoundCommand, account_option, network_option
from ape.logging import logger

import scripts.deployment_utils as deploy_utils


def _get_deployed_contracts():  # noqa: F
    pass


def _save_deployed_contracts():
    pass


@click.group(short_help="Deploy the project")
def cli():
    pass


@cli.command(cls=NetworkBoundCommand)
@network_option()
@account_option()
def deploy_and_test_infra(network, account):

    if account.alias == "fiddydeployer":
        account.set_autosign(True)

    if "ethereum:mainnet-fork" in network:
        account = accounts["0xbabe61887f1de2713c6f97e567623453d3c79f67"]

    for _network, data in deploy_utils.curve_dao_network_settings.items():

        if _network in network:

            owner = data.dao_ownership_contract
            fee_receiver = data.fee_receiver_address2

    assert owner, f"Curve's DAO contracts may not be on {network}."
    assert fee_receiver, f"Curve's DAO contracts may not be on {network}."

    with accounts.use_sender(account):

        # --------------------- Deploy math, views, blueprints ---------------------

        math_contract = project.CurveStableSwapNGMath.deploy()
        views_contract = project.CurveStableSwapNGViews.deploy()
        plain_blueprint_contract = deploy_utils.deploy_blueprint(project.CurveStableSwapNG, account)
        meta_blueprint_contract = deploy_utils.deploy_blueprint(project.CurveStableSwapMetaNG, account)
        gauge_blueprint_contract = deploy_utils.deploy_blueprint(project.LiquidityGauge, account)

        # --------------------- DEPLOY FACTORY ---------------------------

        factory = project.CurveStableSwapFactoryNG.deploy(
            deploy_utils.curve_dao_network_settings[network],  # fee_receiver
            deploy_utils.FIDDYRESEARCH,  # owner (temporary)
        )

        factory.set_gauge_implementation(gauge_blueprint_contract)
        factory.set_views_implementation(views_contract)
        factory.set_math_implementation(math_contract)

        factory.set_pool_implementations(0, plain_blueprint_contract)
        factory.set_metapool_implementations(0, meta_blueprint_contract)

        # -------------------------- Add base pools --------------------------

        base_pool_data = deploy_utils.base_pool_list[network]
        if base_pool_data:  # check if network has base pools:
            for data in base_pool_data:
                factory.add_base_pool(
                    data.pool,
                    data.lp_token,
                    data.coins,
                    data.asset_types,
                    data.n_coins,
                )

        # -------------------------- Set up metaregistry --------------------------

        metaregistry_address = deploy_utils.curve_dao_network_settings[network].metaregistry_address

        if metaregistry_address:

            metaregistry = Contract(metaregistry_address)
            boss = Contract(metaregistry.owner())

            # set up metaregistry integration:
            logger.info("Integrate into Metaregistry ...")
            logger.info("Deploying Factory handler to integrate it to the metaregistry:")
            factory_handler = account.deploy(
                project.CurveStableSwapFactoryNGHandler,
                factory.address,
                deploy_utils.curve_dao_network_settings[network].base_pool_address,
                **deploy_utils._get_tx_params(),
            )

            boss.execute(
                metaregistry.address,
                metaregistry.add_registry_handler.encode_input(factory_handler),
                **deploy_utils._get_tx_params(),
            )
