import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


@pytest.mark.all_token_pairs
@pytest.mark.parametrize("sending,receiving", [(0, 1), (1, 0)])
# todo - rename into test_get_dy - because that's the main test goal
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

    amount = 1_000 * 10 ** decimals[sending]

    initial_receiving = (
        pool_tokens[receiving].balanceOf(bob) if pool_type == 0 else underlying_tokens[receiving].balanceOf(bob)
    )

    min_dy = swap.get_dy(sending, receiving, amount)
    # pool_balance_token_in = pool_tokens[sending].balanceOf(swap.address)
    pool_balance_token_in = swap.balances(sending)
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
        # min_dy is thus roughly inflated by token_in (now rebased) held by pool
        # approximate assert because of how min_dy is approximated
        min_dy += (pool_balance_token_in) // 1000000  # that works because pool has equal balances more or less
        assert receiving_token_diff == pytest.approx(min_dy, rel=0.01 / 100)  # 0.01% relative error

    elif pool_type == 0 and pool_token_types[receiving] == 2 and pool_token_types[sending] != 2:
        # 2) token_in = nonrebasing, token_out = rebasing
        # because pool doesn't assume dy to be rebasing, estimated min_dy is slightly less than
        # actual received dy (inflated upon transfer)
        # approximate assert handles this, absolute error not larger than single rebasing delta
        assert receiving_token_diff == pytest.approx(min_dy, abs=final_receiving / 1000000)

    elif pool_type == 0 and pool_token_types[receiving] == pool_token_types[sending] == 2:
        # 3) token_in = rebasing, token_out = rebasing
        # here get_dy acts on smaller dx, but dx is inflated upon transfer => more dy, and additionally dy
        # is inflated upon transfer_out
        # thus effects are cumulative
        min_dy += (pool_balance_token_in) // 1000000
        assert receiving_token_diff == pytest.approx(min_dy, abs=final_receiving // 1000000)

    elif pool_type == 1 and metapool_token_type == 2:  # metapool: rebasing token vs LP
        # this case is identical to 1a) or 2) (depending on swap direction)
        # in metapools LP tokens are always basic and always on idx 1, so idx 0 is rebasing here
        if sending == 0:  # user sends rebasing token
            # if sending = 0 and receiving = 1, we have: token_in = rebasing, token_out = nonrebasing [case 1a)]
            min_dy += (pool_balance_token_in) // 1000000  # that works because pool has equal balances more or less
            # 1% relative error - we are in metapool, and not perfectly balanced
            assert receiving_token_diff == pytest.approx(min_dy, rel=0.01 / 100)
        else:
            # if sending = 1 and receiving = 0, we have: token_in = nonrebasing, token_out = rebasing
            assert receiving_token_diff == pytest.approx(min_dy, abs=final_receiving // 1000000)
    else:
        # no rebasing tokens, so everything must be precise
        assert abs(receiving_token_diff - min_dy) <= 1


# @pytest.mark.only_meta_pool
@pytest.mark.all_token_pairs
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
    # @note - this test has lots of edge-cases, we need to consider rebase effects, oracle rates, etc.
    # however, we assume that pool imbalance is so high, that it will always dominate these effects
    # for this reason we do not consider them all in this test, as in 'balanced' test above

    # amount to add and to swap, should be large enough
    amount = min([swap.balances(i) for i in range(2)])  # min max not critical here

    # imbalance is always towards token_out, so we always get more token_out than token_in
    amounts_add = [0, 0]
    amounts_add[sending] = 0
    amounts_add[receiving] = amount
    swap.add_liquidity(amounts_add, 0, sender=bob)

    # pool state is unbalanced - it has some token_in (sending) from initializations and a lot of token_out (receiving)
    assert swap.balances(receiving) > swap.balances(sending)

    # min_dy_sending - send scarcer asset, receive more abundant asset
    min_dy_sending = swap.get_dy(sending, receiving, amount)
    # min_dy_receiving - send more abundant asset receive scarcer asset,
    min_dy_receiving = swap.get_dy(receiving, sending, amount)

    # oracle treatment (so that test works even for large-deviation oracle tokens)
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

    # min_dy_sending must be more than min_dy_receiving
    assert min_dy_sending * rate > min_dy_receiving
