import pytest

pytestmark = pytest.mark.usefixtures("initial_setup")


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
    amount = 1000 * 10 ** decimals[sending]
    initial_receiving = (
        pool_tokens[receiving].balanceOf(bob) if pool_type == 0 else underlying_tokens[receiving].balanceOf(bob)
    )

    min_dy = swap.get_dy(sending, receiving, amount)
    # apply rebasing for expected dy
    # Down rebasing breaks dy
    if pool_type == 0 and pool_token_types[sending] == 2 and sending == 1:
        min_dy -= pool_tokens[sending].balanceOf(swap.address) // 1000000

    swap.exchange(sending, receiving, amount, min_dy - 1, sender=bob)

    if pool_type == 0:
        received = pool_tokens[receiving].balanceOf(bob)
    else:
        received = underlying_tokens[receiving].balanceOf(bob)

    if (pool_type == 0 and 2 in pool_token_types) or (pool_type == 1 and metapool_token_type == 2):
        assert abs(received - min_dy - initial_receiving) == pytest.approx(1, abs=received // 1000000)
    else:
        assert abs(received - min_dy - initial_receiving) <= 1


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
