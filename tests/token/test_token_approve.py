import boa
import pytest
from eip712 import EIP712Message
from eth_account._utils.signing import to_bytes32

from tests.utils.transactions import call_returning_result_and_logs


@pytest.mark.parametrize("idx", range(4))
def test_initial_approval_is_zero(swap, alice, accounts, idx, set_metapool_implementations):
    assert swap.allowance(alice, accounts[idx]) == 0


def test_approve(swap, alice, bob):
    swap.approve(bob, 10**19, sender=alice)
    assert swap.allowance(alice, bob) == 10**19


def test_modify_approve_zero_nonzero(swap, alice, bob):
    with boa.env.prank(alice):
        swap.approve(bob, 10**19)
        swap.approve(bob, 0)
        swap.approve(bob, 12345678)

    assert swap.allowance(alice, bob) == 12345678


def test_revoke_approve(swap, alice, bob):
    with boa.env.prank(alice):
        swap.approve(bob, 10**19)
        swap.approve(bob, 0)

    assert swap.allowance(alice, bob) == 0


def test_approve_self(swap, alice):
    swap.approve(alice, 10**19, sender=alice)
    assert swap.allowance(alice, alice) == 10**19


def test_only_affects_target(swap, alice, bob):
    swap.approve(bob, 10**19, sender=alice)
    assert swap.allowance(bob, alice) == 0


def test_returns_true(swap, alice, bob):
    tx = swap.approve(bob, 10**19, sender=alice)
    assert tx is True


def test_approval_event_fires(alice, bob, swap):
    value = 10**19
    res, events = call_returning_result_and_logs(swap, "approve", bob, value, sender=alice)

    assert res is True
    assert len(events) == 1
    assert repr(events[0]) == f"Approval(owner={alice}, spender={bob}, value={value})"


def test_infinite_approval(initial_setup, swap, alice, bob):
    swap.approve(bob, 2**256 - 1, sender=alice)
    swap.transferFrom(alice, bob, 10**18, sender=bob)
    assert swap.allowance(alice, bob) == 2**256 - 1


def permit_class(swap) -> type[EIP712Message]:
    class Permit(EIP712Message):
        # EIP-712 Domain Fields
        _name_: "string" = swap.name()  # noqa: F821
        _version_: "string" = swap.version()  # noqa: F821
        _chainId_: "uint256" = boa.env.evm.chain.chain_id  # noqa: F821
        _verifyingContract_: "address" = swap.address  # noqa: F821
        _salt_: "bytes32" = swap.salt()  # noqa: F821

        # EIP-2612 Data Fields
        owner: "address"  # noqa: F821
        spender: "address"  # noqa: F821
        value: "uint256"  # noqa: F821
        nonce: "uint256"  # noqa: F821
        deadline: "uint256" = 2**256 - 1  # noqa: F821

    return Permit


def test_permit(eth_acc, bob, swap):
    value = 2**256 - 1
    permit = permit_class(swap)(owner=eth_acc.address, spender=bob, value=value, nonce=0)
    sig = eth_acc.sign_message(permit.signable_message)

    res, events = call_returning_result_and_logs(
        swap,
        "permit",
        eth_acc.address,
        bob,
        2**256 - 1,
        2**256 - 1,
        sig.v,
        to_bytes32(sig.r),
        to_bytes32(sig.s),
        sender=bob,
    )

    assert swap.allowance(eth_acc.address, bob) == 2**256 - 1
    assert res is True
    assert len(events) == 1
    assert repr(events[0]) == f"Approval(owner={eth_acc.address}, spender={bob}, value={value})"
    assert swap.nonces(eth_acc.address) == 1


def test_permit_contract(eth_acc, bob, swap):
    # based on https://eips.ethereum.org/EIPS/eip-1271
    src = """
        # pragma version 0.3.10
        OWNER: public(immutable(address))

        @external
        def __init__():
            OWNER = msg.sender

        @view
        @external
        def isValidSignature(_hash: bytes32, _signature: Bytes[65]) -> bytes32:
            signer: address = self._recover_signer(_hash, _signature)
            if signer == OWNER:
                return 0x1626ba7e00000000000000000000000000000000000000000000000000000000
            return 0xffffffff00000000000000000000000000000000000000000000000000000000

        @view
        @internal
        def _recover_signer(_hash: bytes32, _signature: Bytes[65]) -> address:
            v: uint256 = convert(slice(_signature, 64, 1), uint256)
            r: uint256 = convert(slice(_signature, 0, 32), uint256)
            s: uint256 = convert(slice(_signature, 32, 32), uint256)
            return ecrecover(_hash, v, r, s)
    """
    with boa.env.prank(eth_acc.address):
        mock_contract = boa.loads(src)

    permit = permit_class(swap)(
        owner=mock_contract.address, spender=bob, value=2**256 - 1, nonce=0
    )
    sig = eth_acc.sign_message(permit.signable_message)

    res, events = call_returning_result_and_logs(
        swap,
        "permit",
        mock_contract.address,
        bob,
        2**256 - 1,
        2**256 - 1,
        sig.v,
        to_bytes32(sig.r),
        to_bytes32(sig.s),
        sender=bob,
    )
    assert swap.allowance(mock_contract.address, bob) == 2**256 - 1
    assert res is True
    assert len(events) == 1
