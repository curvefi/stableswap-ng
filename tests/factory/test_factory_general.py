def test_get_A(factory, swap):
    assert factory.get_A(swap.address) == swap.A()


def test_get_fees(factory, swap):
    assert factory.get_fees(swap.address) == (swap.fee(), swap.admin_fee())


def test_get_admin_balances(factory, swap, pool_size):
    balances = [swap.admin_balances(i) for i in range(pool_size)]
    assert factory.get_admin_balances(swap.address) == balances


def test_fee_receiver(factory, fee_receiver):
    assert factory.fee_receiver() == fee_receiver
