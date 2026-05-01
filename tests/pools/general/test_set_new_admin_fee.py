import boa
import pytest


@pytest.mark.parametrize("admin_fee", [0, 10**2, 10**6, 10**10])
def test_default_behavior(admin_fee, swap, owner):
    swap.set_new_admin_fee(admin_fee, sender=owner)
    assert swap.admin_fee() == admin_fee


def test_only_admin(swap):
    with boa.reverts(dev="only admin"):
        swap.set_new_admin_fee(10**2)


def test_max_admin_fee(swap, owner):
    with boa.reverts(dev="more than 100%"):
        swap.set_new_admin_fee(10**10 + 1, sender=owner)
