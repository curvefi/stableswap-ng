import boa
from boa.vyper.contract import VyperContract
from eth_utils import to_checksum_address


def mint_for_testing(user: str, amount, token_contract: VyperContract | None, mint_eth: bool = False) -> None:
    assert token_contract is not None or mint_eth

    user = to_checksum_address(user)

    if mint_eth:
        boa.env.set_balance(user, boa.env.get_balance(user) + amount)
    else:
        if token_contract.symbol() == "WETH":
            boa.env.set_balance(user, boa.env.get_balance(user) + amount)
            with boa.env.prank(user):
                token_contract.deposit(value=amount)
        else:
            with boa.env.prank(user):
                token_contract._mint_for_testing(user, amount)
