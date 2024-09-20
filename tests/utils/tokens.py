import boa

# from boa.contracts.vyper import VyperContract
from boa.contracts.vyper.vyper_contract import VyperContract
from eth_utils import to_checksum_address


def mint_for_testing(
    user: str, amount: int, token_contract: VyperContract | None, mint_eth: bool = False
) -> None:
    assert token_contract is not None or mint_eth

    user = to_checksum_address(user)

    if mint_eth:
        boa.env.set_balance(user, amount)
    else:
        balance = token_contract.balanceOf(user)
        if balance < amount:
            _amount_to_add = amount - balance
            if token_contract.symbol() == "WETH":
                boa.env.set_balance(user, boa.env.get_balance(user) + _amount_to_add)
                with boa.env.prank(user):
                    token_contract.deposit(value=_amount_to_add)
            else:
                with boa.env.prank(user):
                    token_contract._mint_for_testing(user, _amount_to_add)
