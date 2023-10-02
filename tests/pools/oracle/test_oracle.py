import boa
import pytest

from tests.fixtures.accounts import add_base_pool_liquidity, mint_account
from tests.fixtures.constants import INITIAL_AMOUNT
from tests.utils.tokens import mint_for_testing

DEPOSIT_AMOUNT = INITIAL_AMOUNT // 100


@pytest.mark.only_for_token_types(1)
class TestOracle:
    class TestInitialLiquidity:
        @pytest.fixture(scope="module")
        def initial_setup_alice(
            self,
            alice,
            deposit_amounts,
            swap,
            pool_type,
            base_pool,
            base_pool_tokens,
            base_pool_decimals,
            base_pool_lp_token,
            initial_balance,
            initial_amounts,
            pool_tokens,
            underlying_tokens,
        ):
            with boa.env.anchor():
                mint_for_testing(alice, 1 * 10**18, None, True)

                if pool_type == 0:
                    mint_account(alice, pool_tokens, initial_balance, initial_amounts)
                    with boa.env.prank(alice):
                        for token in pool_tokens:
                            token.approve(swap.address, 2**256 - 1)

                else:
                    add_base_pool_liquidity(alice, base_pool, base_pool_tokens, base_pool_decimals)
                    mint_for_testing(alice, initial_amounts[0], underlying_tokens[0], False)

                    with boa.env.prank(alice):
                        for token in underlying_tokens:
                            token.approve(swap.address, 2**256 - 1)

                yield

        def test_initial_liquidity(
            self,
            alice,
            initial_setup_alice,
            swap,
            pool_type,
            pool_token_types,
            metapool_token_type,
            decimals,
            meta_decimals,
            pool_tokens,
            metapool_token,
        ):
            amounts = []

            if pool_type == 0:
                for i, t in enumerate(pool_token_types):
                    if t != 1:
                        amounts.append(DEPOSIT_AMOUNT * 10 ** decimals[i])
                    else:
                        amounts.append(DEPOSIT_AMOUNT * 10 ** decimals[i] * 10**18 // pool_tokens[i].exchangeRate())
            else:
                if metapool_token_type == 1:
                    amounts = [
                        DEPOSIT_AMOUNT * 10**meta_decimals * 10**18 // metapool_token.exchangeRate(),
                        DEPOSIT_AMOUNT * 10**18,
                    ]
                else:
                    amounts = [DEPOSIT_AMOUNT * 10**meta_decimals, DEPOSIT_AMOUNT * 10**18]

            swap.add_liquidity(amounts, 0, sender=alice)
            swap.add_liquidity(amounts, 0, sender=alice)

            assert swap.admin_balances(0) == 0
            assert swap.admin_balances(1) == 0

        def test_oracles(self, alice, swap, pool_size, pool_type, pool_token_types, metapool_token_type):
            assert swap._storage.oracles.get() != [0] * pool_size

        def test_get_dy(
            self,
            alice,
            initial_setup_alice,
            swap,
            pool_type,
            pool_token_types,
            metapool_token_type,
            decimals,
            meta_decimals,
            pool_tokens,
            metapool_token,
        ):
            amounts = []

            if pool_type == 0:
                for i, t in enumerate(pool_token_types):
                    if t != 1:
                        amounts.append(DEPOSIT_AMOUNT * 10 ** decimals[i])
                    else:
                        amounts.append(DEPOSIT_AMOUNT * 10 ** decimals[i] * 10**18 // pool_tokens[i].exchangeRate())
            else:
                if metapool_token_type == 1:
                    amounts = [
                        DEPOSIT_AMOUNT * 10**meta_decimals * 10**18 // metapool_token.exchangeRate(),
                        DEPOSIT_AMOUNT * 10**18,
                    ]
                else:
                    amounts = [DEPOSIT_AMOUNT * 10**meta_decimals, DEPOSIT_AMOUNT * 10**18]

            swap.add_liquidity(amounts, 0, sender=alice)

            if pool_type == 0:
                rate_1 = 10**18 if pool_token_types[0] != 1 else pool_tokens[0].exchangeRate()
                rate_2 = 10**18 if pool_token_types[1] != 1 else pool_tokens[1].exchangeRate()

                assert swap.get_dy(0, 1, rate_2) == pytest.approx(rate_1, rel=1e-3)

            else:
                rate_1 = 1 if metapool_token_type != 1 else metapool_token.exchangeRate()

                assert swap.get_dy(0, 1, 10**18) == pytest.approx(rate_1, rel=1e-3)
