import boa
import pytest

from tests.utils.tokens import mint_for_testing


# @pytest.mark.skip_rebasing_tokens
@pytest.mark.only_for_pool_type(0)
def test_donate_get_D(bob, swap, underlying_tokens, pool_tokens):

    # check if pool is empty:
    for i in range(swap.N_COINS()):
        assert swap.balances(i) == 0

    # adding liquidity should not bork:
    amounts = [10**17] * swap.N_COINS()

    for token in pool_tokens:
        token.approve(swap, 2**256 - 1, sender=bob)
        mint_for_testing(bob, 10**18, token, False)

    # check if pool is empty (after minting tokenss):
    for i in range(swap.N_COINS()):
        assert swap.balances(i) == 0

    # donate 1 wei and attempt adding liquidity:
    pool_tokens[0].transfer(swap, 10, sender=bob)
    if 2 in swap._immutables.asset_types:
        with boa.reverts():
            # division by zero error expected for rebasing implementation
            swap.add_liquidity(amounts, 0, sender=bob)
    else:
        swap.add_liquidity(amounts, 0, sender=bob)
