import click
from ape import Contract, accounts, project
from ape.cli import NetworkBoundCommand, account_option, network_option
from ape.logging import logger

import scripts.deployment_utils as deploy_utils


@click.group(short_help="Deploy the project")
def cli():
    pass


@cli.command(cls=NetworkBoundCommand)
@network_option()
@account_option()
def deploy_infra(network, account):

    if account.alias == "fiddydeployer":
        account.set_autosign(True)

    for _network, data in deploy_utils.curve_dao_network_settings.items():

        if _network in network:

            owner = data.dao_ownership_contract
            fee_receiver = data.fee_receiver_address2

    assert owner, f"Curve's DAO contracts may not be on {network}."
    assert fee_receiver, f"Curve's DAO contracts may not be on {network}."

    with accounts.use_sender(account):

        # --------------------- Deploy math, views, blueprints ---------------------

        logger.info("Deploying AMM components ...")
        math_contract = project.CurveStableSwapNGMath.deploy()
        views_contract = project.CurveStableSwapNGViews.deploy()
        plain_blueprint_contract = deploy_utils.deploy_blueprint(project.CurveStableSwapNG, account)
        meta_blueprint_contract = deploy_utils.deploy_blueprint(project.CurveStableSwapMetaNG, account)
        gauge_blueprint_contract = deploy_utils.deploy_blueprint(project.LiquidityGauge, account)

        # --------------------- DEPLOY FACTORY ---------------------------

        logger.info("Deploying factory ...")
        factory = project.CurveStableSwapFactoryNG.deploy(
            deploy_utils.curve_dao_network_settings[network],  # fee_receiver
            deploy_utils.FIDDYRESEARCH,  # owner (temporary)
        )

        logger.info("Integrating AMM components into factory ...")

        factory.set_gauge_implementation(gauge_blueprint_contract, **deploy_utils._get_tx_params())
        factory.set_views_implementation(views_contract, **deploy_utils._get_tx_params())
        factory.set_math_implementation(math_contract, **deploy_utils._get_tx_params())

        factory.set_pool_implementations(0, plain_blueprint_contract, **deploy_utils._get_tx_params())
        factory.set_metapool_implementations(0, meta_blueprint_contract, **deploy_utils._get_tx_params())

        # -------------------------- Add base pools --------------------------

        logger.info("Setting up base pools ...")
        base_pool_data = deploy_utils.base_pool_list[network]
        if base_pool_data:  # check if network has base pools:
            for data in base_pool_data:
                factory.add_base_pool(
                    data.pool,
                    data.lp_token,
                    data.coins,
                    data.asset_types,
                    data.n_coins,
                    **deploy_utils._get_tx_params(),
                )


@cli.command(cls=NetworkBoundCommand)
@network_option()
@account_option()
@click.option("--factory", required=True, type=str)
def set_up_registries(network, account, factory):

    if account.alias == "fiddydeployer":
        account.set_autosign(True)

    for _network, data in deploy_utils.curve_dao_network_settings.items():

        if _network in network:

            owner = data.dao_ownership_contract
            fee_receiver = data.fee_receiver_address
            address_provider = Contract(data.address_provider)

    assert owner, f"Curve's DAO contracts may not be on {network}."
    assert fee_receiver, f"Curve's DAO contracts may not be on {network}."

    with accounts.use_sender(account):

        # -------------------------- Register into AddressProvider --------------------------

        max_id = address_provider.max_id()
        description = "Curve StableSwapNG"
        boss = Contract(address_provider.admin())

        # check if account can handle boss:
        account_is_boss_handler = False
        for i in range(2):
            if account.address.lower() == boss.admins(i).lower():
                account_is_boss_handler = True
                break

        assert account_is_boss_handler  # only authorised accounts can write to address provider  # noqa: E501

        for index in range(max_id + 1):
            if address_provider.get_id_info(index).description is description:
                break

        if index == max_id:

            logger.info(f"Adding a new registry provider entry at id: {index + 1}")

            # we're adding a new id
            with accounts.use_sender(account) as account:
                boss.execute(
                    address_provider.address,
                    address_provider.add_new_id.encode_input(factory, description),
                    gas_limit=400000,
                    **deploy_utils._get_tx_params(),
                )

        else:

            assert address_provider.get_id_info(index).description == description

            logger.info(f"Updating existing registry provider entry at id: {index}")

            # we're updating an existing id with the same description:
            with accounts.use_sender(account) as account:
                boss.execute(
                    address_provider.address,
                    address_provider.set_address.encode_input(index, factory),
                    gas_limit=200000,
                    **deploy_utils._get_tx_params(),
                )

        assert address_provider.get_id_info(index).addr.lower() == factory.lower()

        logger.info("AddressProvider integration complete!")

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
                deploy_utils.curve_dao_network_settings[network].base_pool_registry_address,
                **deploy_utils._get_tx_params(),
            )

            boss.execute(
                metaregistry.address,
                metaregistry.add_registry_handler.encode_input(factory_handler),
                **deploy_utils._get_tx_params(),
            )

            logger.info("Metaregistry integration complete!")
