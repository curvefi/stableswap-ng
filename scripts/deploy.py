import click
from ape import accounts
from ape.cli import NetworkBoundCommand, account_option, network_option
from eth_utils import to_checksum_address

import scripts.deployment_utils as deploy_utils


def _get_deployed_contracts():
    pass


def _save_deployed_contracts():
    pass


def _deploy_pool_from_factory():
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
            fee_receiver = data.fee_receiver_address
            weth = to_checksum_address(data.weth_address)

    assert owner, f"Curve's DAO contracts may not be on {network}."
    assert fee_receiver, f"Curve's DAO contracts may not be on {network}."

    # --------------------- DEPLOY FACTORY AND POOL ---------------------------

    factory = deploy_utils.deploy_amm_factory(account, fee_receiver, weth, network)

    pool = _deploy_pool_from_factory(network, account, factory, weth)
    coins = [
        to_checksum_address(pool.coins(0)),
        to_checksum_address(pool.coins(1)),
        to_checksum_address(pool.coins(2)),
    ]

    _account = account
    if "ethereum:mainnet-fork" in network:  # bridge
        _account = accounts["0x8EB8a3b98659Cce290402893d0123abb75E3ab28"]

    deploy_utils.test_deployment(pool, coins, fee_receiver, _account)

    print("Success!")
