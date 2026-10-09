import boa


def test_default_behavior_factory_admin(swap, owner):
    swap.internal._check_admins(sender=owner)


def test_default_behavior_custom_admin(swap):
    alice = boa.env.generate_address("alice")
    swap.eval(f"self.admin = {alice}")

    swap.internal._check_admins(sender=alice)


def test_only_admin(swap):
    with boa.reverts(dev="only admin"):
        swap.internal._check_admins()
