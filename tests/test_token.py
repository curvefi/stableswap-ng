import boa
import pytest
from eip712.messages import EIP712Message
from eth_account._utils.signing import to_bytes32

from tests.utils.transactions import call_returning_result_and_logs

added_liquidity = pytest.mark.usefixtures("initial_setup")


class TestPoolToken:
    class TestTokenApprove:
        @pytest.mark.parametrize("idx", range(4))
        def test_initial_approval_is_zero(self, swap, alice, accounts, idx):
            assert swap.allowance(alice, accounts[idx]) == 0

        def test_approve(self, swap, alice, bob):
            swap.approve(bob, 10**19, sender=alice)
            assert swap.allowance(alice, bob) == 10**19

        def test_modify_approve_zero_nonzero(self, swap, alice, bob):
            with boa.env.prank(alice):
                swap.approve(bob, 10**19)
                swap.approve(bob, 0)
                swap.approve(bob, 12345678)

            assert swap.allowance(alice, bob) == 12345678

        def test_revoke_approve(self, swap, alice, bob):
            with boa.env.prank(alice):
                swap.approve(bob, 10**19)
                swap.approve(bob, 0)

            assert swap.allowance(alice, bob) == 0

        def test_approve_self(self, swap, alice):
            swap.approve(alice, 10**19, sender=alice)
            assert swap.allowance(alice, alice) == 10**19

        def test_only_affects_target(self, swap, alice, bob):
            swap.approve(bob, 10**19, sender=alice)
            assert swap.allowance(bob, alice) == 0

        def test_returns_true(self, swap, alice, bob):
            tx = swap.approve(bob, 10**19, sender=alice)
            assert tx is True

        def test_approval_event_fires(self, alice, bob, swap):
            value = 10**19
            res, events = call_returning_result_and_logs(swap, "approve", bob, value, sender=alice)

            assert res is True
            assert len(events) == 1
            assert repr(events[0]) == f"Approval(owner={alice}, spender={bob}, value={value})"

        @added_liquidity
        def test_infinite_approval(self, swap, alice, bob):
            swap.approve(bob, 2**256 - 1, sender=alice)
            swap.transferFrom(alice, bob, 10**18, sender=bob)

            assert swap.allowance(alice, bob) == 2**256 - 1

        @staticmethod
        def permit_class(swap) -> type[EIP712Message]:
            class Permit(EIP712Message):
                # EIP-712 Domain Fields
                _name_: "string" = swap.name()  # noqa: F821
                _version_: "string" = swap.version()  # noqa: F821
                _chainId_: "uint256" = boa.env.chain.chain_id  # noqa: F821
                _verifyingContract_: "address" = swap.address  # noqa: F821
                _salt_: "bytes32" = swap.salt()  # noqa: F821

                # EIP-2612 Data Fields
                owner: "address"  # noqa: F821
                spender: "address"  # noqa: F821
                value: "uint256"  # noqa: F821
                nonce: "uint256"  # noqa: F821
                deadline: "uint256" = 2**256 - 1  # noqa: F821

            return Permit

        def test_permit(self, eth_acc, bob, swap):
            value = 2**256 - 1
            permit = self.permit_class(swap)(owner=eth_acc.address, spender=bob, value=value, nonce=0)
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

        def test_permit_contract(self, eth_acc, bob, swap):
            # based on https://eips.ethereum.org/EIPS/eip-1271
            src = """
                # @version 0.3.9
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

            permit = self.permit_class(swap)(owner=mock_contract.address, spender=bob, value=2**256 - 1, nonce=0)
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

    @added_liquidity
    class TestTokenTransfer:
        def test_sender_balance_decreases(self, alice, bob, swap):
            sender_balance = swap.balanceOf(alice)
            amount = sender_balance // 4

            swap.transfer(bob, amount, sender=alice)

            assert swap.balanceOf(alice) == sender_balance - amount

        def test_receiver_balance_increases(self, alice, bob, swap):
            receiver_balance = swap.balanceOf(bob)
            amount = swap.balanceOf(alice) // 4

            swap.transfer(bob, amount, sender=alice)

            assert swap.balanceOf(bob) == receiver_balance + amount

        def test_total_supply_not_affected(self, alice, bob, swap):
            total_supply = swap.totalSupply()
            amount = swap.balanceOf(alice)

            swap.transfer(bob, amount, sender=alice)

            assert swap.totalSupply() == total_supply

        def test_returns_true(self, alice, bob, swap):
            amount = swap.balanceOf(alice)
            res = swap.transfer(bob, amount, sender=alice)

            assert res is True

        def test_transfer_full_balance(self, alice, bob, swap):
            amount = swap.balanceOf(alice)
            receiver_balance = swap.balanceOf(bob)

            swap.transfer(bob, amount, sender=alice)

            assert swap.balanceOf(alice) == 0
            assert swap.balanceOf(bob) == receiver_balance + amount

        def test_transfer_zero_tokens(self, alice, bob, swap):
            sender_balance = swap.balanceOf(alice)
            receiver_balance = swap.balanceOf(bob)

            swap.transfer(bob, 0, sender=alice)

            assert swap.balanceOf(alice) == sender_balance
            assert swap.balanceOf(bob) == receiver_balance

        def test_transfer_to_self(self, alice, bob, swap):
            sender_balance = swap.balanceOf(alice)
            amount = sender_balance // 4

            swap.transfer(alice, amount, sender=alice)

            assert swap.balanceOf(alice) == sender_balance

        def test_insufficient_balance(self, alice, bob, swap):
            balance = swap.balanceOf(alice)

            with boa.reverts():
                swap.transfer(bob, balance + 1, sender=alice)

        def test_transfer_event_fires(self, alice, bob, swap):
            amount = swap.balanceOf(alice)
            _, events = call_returning_result_and_logs(swap, "transfer", bob, amount, sender=alice)

            assert len(events) == 1
            assert repr(events[0]) == f"Transfer(sender={alice}, receiver={bob}, value={amount})"

    @added_liquidity
    class TestTokenTransferFrom:
        def test_sender_balance_decreases(self, alice, bob, charlie, swap):
            sender_balance = swap.balanceOf(alice)
            amount = sender_balance // 4

            swap.approve(bob, amount, sender=alice)
            swap.transferFrom(alice, charlie, amount, sender=bob)

            assert swap.balanceOf(alice) == sender_balance - amount

        def test_receiver_balance_increases(self, alice, bob, charlie, swap):
            receiver_balance = swap.balanceOf(charlie)
            amount = swap.balanceOf(alice) // 4

            swap.approve(bob, amount, sender=alice)
            swap.transferFrom(alice, charlie, amount, sender=bob)

            assert swap.balanceOf(charlie) == receiver_balance + amount

        def test_caller_balance_not_affected(self, alice, bob, charlie, swap):
            caller_balance = swap.balanceOf(bob)
            amount = swap.balanceOf(alice)

            swap.approve(bob, amount, sender=alice)
            swap.transferFrom(alice, charlie, amount, sender=bob)

            assert swap.balanceOf(bob) == caller_balance

        def test_caller_approval_affected(self, alice, bob, charlie, swap):
            approval_amount = swap.balanceOf(alice)
            transfer_amount = approval_amount // 4

            swap.approve(bob, approval_amount, sender=alice)
            swap.transferFrom(alice, charlie, transfer_amount, sender=bob)

            assert swap.allowance(alice, bob) == approval_amount - transfer_amount

        def test_receiver_approval_not_affected(self, alice, bob, charlie, swap):
            approval_amount = swap.balanceOf(alice)
            transfer_amount = approval_amount // 4

            swap.approve(bob, approval_amount, sender=alice)
            swap.approve(charlie, approval_amount, sender=alice)
            swap.transferFrom(alice, charlie, transfer_amount, sender=bob)

            assert swap.allowance(alice, charlie) == approval_amount

        def test_total_supply_not_affected(self, alice, bob, charlie, swap):
            total_supply = swap.totalSupply()
            amount = swap.balanceOf(alice)

            swap.approve(bob, amount, sender=alice)
            swap.transferFrom(alice, charlie, amount, sender=bob)

            assert swap.totalSupply() == total_supply

        def test_returns_true(self, alice, bob, charlie, swap):
            amount = swap.balanceOf(alice)
            swap.approve(bob, amount, sender=alice)
            res = swap.transferFrom(alice, charlie, amount, sender=bob)

            assert res is True

        def test_transfer_full_balance(self, alice, bob, charlie, swap):
            amount = swap.balanceOf(alice)
            receiver_balance = swap.balanceOf(charlie)

            swap.approve(bob, amount, sender=alice)
            swap.transferFrom(alice, charlie, amount, sender=bob)

            assert swap.balanceOf(alice) == 0
            assert swap.balanceOf(charlie) == receiver_balance + amount

        def test_transfer_zero_tokens(self, alice, bob, charlie, swap):
            sender_balance = swap.balanceOf(alice)
            receiver_balance = swap.balanceOf(charlie)

            swap.approve(bob, sender_balance, sender=alice)
            swap.transferFrom(alice, charlie, 0, sender=bob)

            assert swap.balanceOf(alice) == sender_balance
            assert swap.balanceOf(charlie) == receiver_balance

        def test_transfer_zero_tokens_without_approval(self, alice, bob, charlie, swap):
            sender_balance = swap.balanceOf(alice)
            receiver_balance = swap.balanceOf(charlie)

            swap.transferFrom(alice, charlie, 0, sender=bob)

            assert swap.balanceOf(alice) == sender_balance
            assert swap.balanceOf(charlie) == receiver_balance

        def test_insufficient_balance(self, alice, bob, charlie, swap):
            balance = swap.balanceOf(alice)

            swap.approve(bob, balance + 1, sender=alice)
            with boa.reverts():
                swap.transferFrom(alice, charlie, balance + 1, sender=bob)

        def test_insufficient_approval(self, alice, bob, charlie, swap):
            balance = swap.balanceOf(alice)

            swap.approve(bob, balance - 1, sender=alice)
            with boa.reverts():
                swap.transferFrom(alice, charlie, balance, sender=bob)

        def test_no_approval(self, alice, bob, charlie, swap):
            balance = swap.balanceOf(alice)

            with boa.reverts():
                swap.transferFrom(alice, charlie, balance, sender=bob)

        def test_revoked_approval(self, alice, bob, charlie, swap):
            balance = swap.balanceOf(alice)

            swap.approve(bob, balance, sender=alice)
            swap.approve(bob, 0, sender=alice)

            with boa.reverts():
                swap.transferFrom(alice, charlie, balance, sender=bob)

        def test_transfer_to_self(self, alice, bob, swap):
            sender_balance = swap.balanceOf(alice)
            amount = sender_balance // 4

            swap.approve(alice, sender_balance, sender=alice)
            swap.transferFrom(alice, alice, amount, sender=alice)

            assert swap.balanceOf(alice) == sender_balance
            assert swap.allowance(alice, alice) == sender_balance - amount

        def test_transfer_to_self_no_approval(self, alice, bob, swap):
            amount = swap.balanceOf(alice)

            with boa.reverts():
                swap.transferFrom(alice, alice, amount, sender=alice)

        def test_transfer_event_fires(self, alice, bob, charlie, swap):
            amount = swap.balanceOf(alice)

            swap.approve(bob, amount, sender=alice)
            _, events = call_returning_result_and_logs(swap, "transferFrom", alice, charlie, amount, sender=bob)

            assert len(events) == 1
            assert repr(events[0]) == f"Transfer(sender={alice}, receiver={charlie}, value={amount})"
