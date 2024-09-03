import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


# @pytest.mark.only_basic_pool
@pytest.mark.extensive_token_pairs
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_min_dy(
    bob,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    pool_token_types,
    metapool_token_type,
    sending,
    receiving,
    decimals,
):
    # debug stops for investigations
    if pool_token_types[receiving] == 2:
        pass
    if pool_token_types[sending] == 2:
        pass
    if pool_token_types[receiving] == pool_token_types[sending] == 2:
        pass

    amount = 1000 * 10 ** decimals[sending]

    initial_receiving = (
        pool_tokens[receiving].balanceOf(bob) if pool_type == 0 else underlying_tokens[receiving].balanceOf(bob)
    )

    min_dy = swap.get_dy(sending, receiving, amount)
    pool_balance_token_in = pool_tokens[sending].balanceOf(swap.address)

    # swap.exchange(sending, receiving, amount, min_dy - 1, sender=bob)
    # no slippage here, we test min_dy extensively later on
    swap.exchange(sending, receiving, amount, 0, sender=bob)
    if pool_type == 0:
        final_receiving = pool_tokens[receiving].balanceOf(bob)
    else:
        final_receiving = underlying_tokens[receiving].balanceOf(bob)

    receiving_token_diff = final_receiving - initial_receiving

    if pool_type == 0 and pool_token_types[sending] == 2 and pool_token_types[receiving] != 2:
        # 1) token_in = rebasing, token_out = nonrebasing
        # because pool fixes dx honestly by comparing prev balance to balance after transfer_in,
        # we have slightly more dx (due to rebase on transfer) than when we are calling get_dy()
        # as a result, we receive slightly more dy than estimated min_dy
        # we correct for expected min_dy (inflate it) by value of pool balances after transfer_in
        # min_dy is thus roughly scaled by token_in (now rebased) held by pool
        # approximate assert because of how min_dy is approximated, in case of almost-balanced pool 5% tolerance
        if pool_token_types[receiving] == 0:
            # plain token_out, we may assume perfect pool balance
            min_dy += (pool_balance_token_in) // 1000000  # that works because pool has equal balances more or less
        elif pool_token_types[receiving] == 1:
            # for oracle token_out pool isn't balanced because of exchange_rate, so we adjust testing proportionally
            min_dy += (
                pool_balance_token_in / (pool_tokens[receiving].exchange_rate() // pool_tokens[receiving].decimals())
            ) // 1000000
        assert abs(receiving_token_diff) == pytest.approx(min_dy, rel=5e-02)
    elif pool_type == 0 and pool_token_types[receiving] == 2 and pool_token_types[sending] != 2:
        # 2) token_in = nonrebasing, token_out = rebasing
        # because pool doesn't assume dy to be rebasing, estimated min_dy is slightly less than
        # actual received dy (inflated upon transfer)
        # approximate assert handles this, absolute error not larger than single rebasing delta
        assert abs(receiving_token_diff - min_dy) == pytest.approx(1, abs=final_receiving // 1000000)
        # pass
    elif pool_type == 0 and pool_token_types[receiving] == pool_token_types[sending] == 2:
        # 3) token_in = rebasing, token_out = rebasing
        # here get_dy acts on smaller dx, but dx is inflated upon transfer => more dy, and additionally dy
        # is inflated upon transfer_out
        # thus effects are cumulative
        min_dy += (pool_balance_token_in) // 1000000
        assert abs(receiving_token_diff - min_dy) == pytest.approx(1, abs=final_receiving // 1000000)
    elif pool_type == 1 and pool_token_types[receiving] == pool_token_types[sending] == 2:
        pass
    else:
        # no rebasing tokens, so everything must be precise
        assert abs(receiving_token_diff - min_dy) <= 1


@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
def test_min_dy_imbalanced(
    bob,
    swap,
    pool_type,
    pool_tokens,
    underlying_tokens,
    pool_token_types,
    metapool_token_type,
    sending,
    receiving,
    decimals,
):
    amounts = [1_500_000 * 10**i for i in decimals]
    scaler = amounts.copy()  # used to scale token amounts when decimals are different

    amounts[sending] = 0
    amounts[receiving] = amounts[receiving]

    swap.add_liquidity(amounts, 0, sender=bob)

    # oracle
    rate = 1
    if pool_type == 0:
        if pool_token_types[sending] == 1:
            rate = rate / (pool_tokens[sending].exchangeRate() / 10**18)
        if pool_token_types[receiving] == 1:
            rate = rate * (pool_tokens[receiving].exchangeRate() / 10**18)

    elif pool_type == 1:
        if metapool_token_type == 1:
            if sending == 0:
                rate = rate / (underlying_tokens[0].exchangeRate() / 10**18)

            if receiving == 0:
                rate = rate * (underlying_tokens[0].exchangeRate() / 10**18)

    # we need to scale these appropriately for tokens with different decimal values
    min_dy_sending = swap.get_dy(sending, receiving, scaler[sending]) / scaler[receiving]
    min_dy_receiving = swap.get_dy(receiving, sending, scaler[receiving]) / scaler[sending]

    assert min_dy_sending * rate > min_dy_receiving
