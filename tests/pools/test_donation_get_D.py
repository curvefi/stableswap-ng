import boa

from tests.utils import get_asset_types_in_pool
from tests.utils.tokens import mint_for_testing


def test_donate_get_D(bob, basic_swap, underlying_tokens, pool_tokens):
    # check if pool is empty:
    for i in range(basic_swap.N_COINS()):
        assert basic_swap.balances(i) == 0

    # adding liquidity should not bork:
    amounts = [10**17] * basic_swap.N_COINS()

    for token in pool_tokens:
        token.approve(basic_swap, 2**256 - 1, sender=bob)
        mint_for_testing(bob, 10**18, token, False)

    # check if pool is empty (after minting tokenss):
    for i in range(basic_swap.N_COINS()):
        assert basic_swap.balances(i) == 0

    # donate 1 wei and attempt adding liquidity:
    pool_tokens[0].transfer(basic_swap, 10, sender=bob)
    if 2 in get_asset_types_in_pool(basic_swap):
        with boa.reverts():
            # division by zero error expected for rebasing implementation
            basic_swap.add_liquidity(amounts, 0, sender=bob)
    else:
        basic_swap.add_liquidity(amounts, 0, sender=bob)
