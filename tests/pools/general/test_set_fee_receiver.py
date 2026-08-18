import boa


def test_default_fee_receiver_is_zero(swap):
    assert swap.pool_fee_receiver() == boa.eval("empty(address)")


def test_set_fee_receiver_by_factory_admin(swap, owner):
    new_receiver = boa.env.generate_address("new_receiver")
    swap.set_fee_receiver(new_receiver, sender=owner)
    assert swap.pool_fee_receiver() == new_receiver


def test_set_fee_receiver_by_pool_admin(swap):
    pool_admin = boa.env.generate_address("pool_admin")
    new_receiver = boa.env.generate_address("new_receiver")

    swap.eval(f"self.admin = {pool_admin}")
    swap.set_fee_receiver(new_receiver, sender=pool_admin)

    assert swap.pool_fee_receiver() == new_receiver


def test_set_fee_receiver_only_admin(swap):
    new_receiver = boa.env.generate_address("new_receiver")
    with boa.reverts(dev="only admin"):
        swap.set_fee_receiver(new_receiver)


def test_set_fee_receiver_event(swap, owner):
    new_receiver = boa.env.generate_address("new_receiver")
    swap.set_fee_receiver(new_receiver, sender=owner)

    logs = swap.get_logs()
    assert len(logs) == 1
    assert logs[0].event_type.name == "UpdatePoolFeeReceiver"
    assert logs[0].args[0] == boa.eval("empty(address)")  # old_receiver
    assert logs[0].args[1] == new_receiver  # new_receiver


def test_set_fee_receiver_event_with_old_receiver(swap, owner):
    old_receiver = boa.env.generate_address("old_receiver")
    new_receiver = boa.env.generate_address("new_receiver")

    swap.set_fee_receiver(old_receiver, sender=owner)
    swap.set_fee_receiver(new_receiver, sender=owner)

    logs = swap.get_logs()
    assert len(logs) == 1
    assert logs[0].event_type.name == "UpdatePoolFeeReceiver"
    assert logs[0].args[0] == old_receiver
    assert logs[0].args[1] == new_receiver
