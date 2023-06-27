import boa
from boa.vyper.contract import VyperContract
from eth_utils import to_checksum_address


def mint_for_testing(
    user: str, amount, token_contract: VyperContract | None, mint_eth: bool = False, is_rebase: bool = False
) -> None:
    assert token_contract is not None or mint_eth

    user = to_checksum_address(user)

    if mint_eth:
        boa.env.set_balance(user, boa.env.get_balance(user) + amount)
    else:
        if token_contract.symbol() == "WETH":
            boa.env.set_balance(user, boa.env.get_balance(user) + amount)
            with boa.env.prank(user):
                token_contract.deposit(value=amount)
        elif not is_rebase:
            token_contract.eval(f"self.totalSupply += {amount}")
            token_contract.eval(f"self.balanceOf[{user}] += {amount}")
            token_contract.eval(f"log Transfer(empty(address), {user}, {amount})")
        else:
            token_contract.eval(f"self.totalCoin += {amount}")
            token_contract.eval(f"self.totalShares += self._get_shares_by_coins({amount})")
            token_contract.eval(f"self.shares[{user}] += self._get_shares_by_coins({amount})")
            token_contract.eval(f"log Transfer(empty(address), {user}, {amount})")
            token_contract.eval(f"log TransferShares(empty(address), {user}, self._get_shares_by_coins({amount}))")
