import boa

MIN_RAMP_TIME = 86400


def test_ramp_A(owner, swap):
    initial_A = swap.initial_A() // 100
    future_time = boa.env.evm.patch.timestamp + MIN_RAMP_TIME + 5

    swap.ramp_A(initial_A * 2, future_time, sender=owner)

    assert swap.initial_A() // 100 == initial_A
    assert swap.future_A() // 100 == initial_A * 2
    assert swap.initial_A_time() == boa.env.evm.patch.timestamp
    assert swap.future_A_time() == future_time


def test_ramp_A_final(owner, swap):
    initial_A = swap.initial_A() // 100
    future_time = boa.env.evm.patch.timestamp + 1000000

    swap.ramp_A(initial_A * 2, future_time, sender=owner)

    boa.env.time_travel(1000000)
    assert swap.A() == initial_A * 2


def test_ramp_A_value_up(owner, swap):
    initial_timestamp = boa.env.evm.patch.timestamp
    initial_A = swap.initial_A() // 100
    future_time = initial_timestamp + 1000000
    swap.ramp_A(initial_A * 2, future_time, sender=owner)

    duration = future_time - initial_timestamp

    while boa.env.evm.patch.timestamp < future_time:
        boa.env.time_travel(100000)
        expected = int(initial_A + ((boa.env.evm.patch.timestamp - initial_timestamp) / duration) * initial_A)
        assert 0.999 < expected / swap.A() <= 1


def test_ramp_A_value_down(owner, swap):
    initial_timestamp = boa.env.evm.patch.timestamp
    initial_A = swap.initial_A() // 100
    future_time = initial_timestamp + 1000000
    swap.ramp_A(initial_A // 10, future_time, sender=owner)

    duration = future_time - initial_timestamp

    while boa.env.evm.patch.timestamp < future_time:
        boa.env.time_travel(100000)
        expected = int(
            initial_A - ((boa.env.evm.patch.timestamp - initial_timestamp) / duration) * (initial_A // 10 * 9)
        )
        if expected == 0:
            assert swap.A() == initial_A // 10
        else:
            assert abs(swap.A() - expected) <= 1


def test_stop_ramp_A(owner, swap):
    initial_A = swap.initial_A() // 100
    future_time = boa.env.evm.patch.timestamp + 1000000
    swap.ramp_A(initial_A * 2, future_time, sender=owner)

    boa.env.time_travel(31337)

    current_A = swap.A()

    swap.stop_ramp_A(sender=owner)

    assert swap.initial_A() // 100 == current_A
    assert swap.future_A() // 100 == current_A
    assert swap.initial_A_time() == boa.env.evm.patch.timestamp
    assert swap.future_A_time() == boa.env.evm.patch.timestamp


def test_ramp_A_only_owner(bob, swap):
    with boa.reverts():
        swap.ramp_A(0, boa.env.evm.patch.timestamp + 1000000, sender=bob)


def test_ramp_A_insufficient_time(owner, swap):
    with boa.reverts():
        swap.ramp_A(0, boa.env.evm.patch.timestamp + MIN_RAMP_TIME - 1, sender=owner)


def test_stop_ramp_A_only_owner(bob, swap):
    with boa.reverts():
        swap.stop_ramp_A(sender=bob)
