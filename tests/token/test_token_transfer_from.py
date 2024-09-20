import boa
import pytest

from tests.utils.transactions import call_returning_result_and_logs


@pytest.fixture(autouse=True)
def added_liquidity(initial_setup):
    ...


def test_sender_balance_decreases(alice, bob, charlie, swap):
    sender_balance = swap.balanceOf(alice)
    amount = sender_balance // 4

    swap.approve(bob, amount, sender=alice)
    swap.transferFrom(alice, charlie, amount, sender=bob)

    assert swap.balanceOf(alice) == sender_balance - amount


def test_receiver_balance_increases(alice, bob, charlie, swap):
    receiver_balance = swap.balanceOf(charlie)
    amount = swap.balanceOf(alice) // 4

    swap.approve(bob, amount, sender=alice)
    swap.transferFrom(alice, charlie, amount, sender=bob)

    assert swap.balanceOf(charlie) == receiver_balance + amount


def test_caller_balance_not_affected(alice, bob, charlie, swap):
    caller_balance = swap.balanceOf(bob)
    amount = swap.balanceOf(alice)

    swap.approve(bob, amount, sender=alice)
    swap.transferFrom(alice, charlie, amount, sender=bob)

    assert swap.balanceOf(bob) == caller_balance


def test_caller_approval_affected(alice, bob, charlie, swap):
    approval_amount = swap.balanceOf(alice)
    transfer_amount = approval_amount // 4

    swap.approve(bob, approval_amount, sender=alice)
    swap.transferFrom(alice, charlie, transfer_amount, sender=bob)

    assert swap.allowance(alice, bob) == approval_amount - transfer_amount


def test_receiver_approval_not_affected(alice, bob, charlie, swap):
    approval_amount = swap.balanceOf(alice)
    transfer_amount = approval_amount // 4

    swap.approve(bob, approval_amount, sender=alice)
    swap.approve(charlie, approval_amount, sender=alice)
    swap.transferFrom(alice, charlie, transfer_amount, sender=bob)

    assert swap.allowance(alice, charlie) == approval_amount


def test_total_supply_not_affected(alice, bob, charlie, swap):
    total_supply = swap.totalSupply()
    amount = swap.balanceOf(alice)

    swap.approve(bob, amount, sender=alice)
    swap.transferFrom(alice, charlie, amount, sender=bob)

    assert swap.totalSupply() == total_supply


def test_returns_true(alice, bob, charlie, swap):
    amount = swap.balanceOf(alice)
    swap.approve(bob, amount, sender=alice)
    res = swap.transferFrom(alice, charlie, amount, sender=bob)

    assert res is True


def test_transfer_full_balance(alice, bob, charlie, swap):
    amount = swap.balanceOf(alice)
    receiver_balance = swap.balanceOf(charlie)

    swap.approve(bob, amount, sender=alice)
    swap.transferFrom(alice, charlie, amount, sender=bob)

    assert swap.balanceOf(alice) == 0
    assert swap.balanceOf(charlie) == receiver_balance + amount


def test_transfer_zero_tokens(alice, bob, charlie, swap):
    sender_balance = swap.balanceOf(alice)
    receiver_balance = swap.balanceOf(charlie)

    swap.approve(bob, sender_balance, sender=alice)
    swap.transferFrom(alice, charlie, 0, sender=bob)

    assert swap.balanceOf(alice) == sender_balance
    assert swap.balanceOf(charlie) == receiver_balance


def test_transfer_zero_tokens_without_approval(alice, bob, charlie, swap):
    sender_balance = swap.balanceOf(alice)
    receiver_balance = swap.balanceOf(charlie)

    swap.transferFrom(alice, charlie, 0, sender=bob)

    assert swap.balanceOf(alice) == sender_balance
    assert swap.balanceOf(charlie) == receiver_balance


def test_insufficient_balance(alice, bob, charlie, swap):
    balance = swap.balanceOf(alice)

    swap.approve(bob, balance + 1, sender=alice)
    with boa.reverts():
        swap.transferFrom(alice, charlie, balance + 1, sender=bob)


def test_insufficient_approval(alice, bob, charlie, swap):
    balance = swap.balanceOf(alice)

    swap.approve(bob, balance - 1, sender=alice)
    with boa.reverts():
        swap.transferFrom(alice, charlie, balance, sender=bob)


def test_no_approval(alice, bob, charlie, swap):
    balance = swap.balanceOf(alice)

    with boa.reverts():
        swap.transferFrom(alice, charlie, balance, sender=bob)


def test_revoked_approval(alice, bob, charlie, swap):
    balance = swap.balanceOf(alice)

    swap.approve(bob, balance, sender=alice)
    swap.approve(bob, 0, sender=alice)

    with boa.reverts():
        swap.transferFrom(alice, charlie, balance, sender=bob)


def test_transfer_to_self(alice, bob, swap):
    sender_balance = swap.balanceOf(alice)
    amount = sender_balance // 4

    swap.approve(alice, sender_balance, sender=alice)
    swap.transferFrom(alice, alice, amount, sender=alice)

    assert swap.balanceOf(alice) == sender_balance
    assert swap.allowance(alice, alice) == sender_balance - amount


def test_transfer_to_self_no_approval(alice, bob, swap):
    amount = swap.balanceOf(alice)

    with boa.reverts():
        swap.transferFrom(alice, alice, amount, sender=alice)


def test_transfer_event_fires(alice, bob, charlie, swap):
    amount = swap.balanceOf(alice)

    swap.approve(bob, amount, sender=alice)

    _, events = call_returning_result_and_logs(
        swap, "transferFrom", alice, charlie, amount, sender=bob
    )

    assert len(events) == 2  #
    assert repr(events[0]) == f"Transfer(sender={alice}, receiver={charlie}, value={amount})"
