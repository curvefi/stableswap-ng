import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs


@pytest.fixture(autouse=True)
def added_liquidity(initial_setup): ...


def test_sender_balance_decreases(alice, bob, swap):
    sender_balance = swap.balanceOf(alice)
    amount = sender_balance // 4

    swap.transfer(bob, amount, sender=alice)

    assert swap.balanceOf(alice) == sender_balance - amount


def test_receiver_balance_increases(alice, bob, swap):
    receiver_balance = swap.balanceOf(bob)
    amount = swap.balanceOf(alice) // 4

    swap.transfer(bob, amount, sender=alice)

    assert swap.balanceOf(bob) == receiver_balance + amount


def test_total_supply_not_affected(alice, bob, swap):
    total_supply = swap.totalSupply()
    amount = swap.balanceOf(alice)

    swap.transfer(bob, amount, sender=alice)

    assert swap.totalSupply() == total_supply


def test_returns_true(alice, bob, swap):
    amount = swap.balanceOf(alice)
    res = swap.transfer(bob, amount, sender=alice)

    assert res is True


def test_transfer_full_balance(alice, bob, swap):
    amount = swap.balanceOf(alice)
    receiver_balance = swap.balanceOf(bob)

    swap.transfer(bob, amount, sender=alice)

    assert swap.balanceOf(alice) == 0
    assert swap.balanceOf(bob) == receiver_balance + amount


def test_transfer_zero_tokens(alice, bob, swap):
    sender_balance = swap.balanceOf(alice)
    receiver_balance = swap.balanceOf(bob)

    swap.transfer(bob, 0, sender=alice)

    assert swap.balanceOf(alice) == sender_balance
    assert swap.balanceOf(bob) == receiver_balance


def test_transfer_to_self(alice, bob, swap):
    sender_balance = swap.balanceOf(alice)
    amount = sender_balance // 4

    swap.transfer(alice, amount, sender=alice)

    assert swap.balanceOf(alice) == sender_balance


def test_insufficient_balance(alice, bob, swap):
    balance = swap.balanceOf(alice)

    with boa.reverts():
        swap.transfer(bob, balance + 1, sender=alice)


def test_transfer_event_fires(alice, bob, swap):
    amount = swap.balanceOf(alice)
    _, events = call_returning_result_and_logs(swap, "transfer", bob, amount, sender=alice)

    assert len(events) == 1
    assert repr(events[0]) == f"Transfer(sender={alice}, receiver={bob}, value={amount})"
