import boa
import pytest

# from eip712.messages import EIP712Message


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

        # TODO: add event processing
        # def test_approval_event_fires(self, alice, bob, swap):
        #     tx = swap.approve(bob, 10 ** 19, sender=alice)
        #
        #     events = swap.get_logs()
        #     print(events, type(events[0]))
        #
        #     assert len(tx.events) == 1
        #     assert tx.events["Approval"].values() == [alice, bob, 10 ** 19]

        @pytest.mark.usefixtures("add_initial_liquidity_alice")
        def test_infinite_approval(self, swap, alice, bob):
            swap.approve(bob, 2**256 - 1, sender=alice)
            swap.transferFrom(alice, bob, 10**18, sender=bob)

            assert swap.allowance(alice, bob) == 2**256 - 1

        # def test_permit(self, eth_acc, bob, swap):
        #     class Permit(EIP712Message):
        #         # EIP-712 Domain Fields
        #         _name_: "string" = swap.name()  # noqa: F821
        #         _version_: "string" = swap.version()  # noqa: F821
        #         _chainId_: "uint256" = boa.env.chain.chain_id  # noqa: F821
        #         _verifyingContract_: "address" = swap.address  # noqa: F821
        #
        #         # EIP-2612 Data Fields
        #         owner: "address"  # noqa: F821
        #         spender: "address"  # noqa: F821
        #         value: "uint256"  # noqa: F821
        #         nonce: "uint256"  # noqa: F821
        #         deadline: "uint256" = 2 ** 256 - 1  # noqa: F821
        #
        #     permit = Permit(owner=eth_acc.address, spender=bob, value=2 ** 256 - 1, nonce=0)
        #     sig = eth_acc.sign_message(permit.signable_message)
        #
        #     with boa.env.prank(bob):
        #         tx = swap.permit(eth_acc.address, bob, 2 ** 256 - 1, 2 ** 256 - 1, sig.v, sig.r, sig.s)
        #
        #     assert swap.allowance(eth_acc.address, bob) == 2 ** 256 - 1
        #     assert tx is True
        #     assert len(swap.get_logs()) == 1
        #     assert swap.get_logs().events["Approval"].values() == [eth_acc.address.address, bob, 2 ** 256 - 1]
        #     assert swap.nonces(eth_acc.address) == 1
        #
        # def test_permit_contract(accounts, bob, chain, swap, web3):
        #     src = """
        #         @view
        #         @external
        #         def isValidSignature(_hash: bytes32, _sig: Bytes[65]) -> bytes32:
        #     return 0x1626ba7e00000000000000000000000000000000000000000000000000000000
        #     """
        #     mock_contract = brownie.compile_source(src, vyper_version="0.3.1").Vyper.deploy({"from": bob})
        #     alice = accounts.add("0x416b8a7d9290502f5661da81f0cf43893e3d19cb9aea3c426cfb36e8186e9c09")
        #
        #     class Permit(EIP712Message):
        #         # EIP-712 Domain Fields
        #         _name_: "string" = swap.name()  # noqa: F821
        #         _version_: "string" = swap.version()  # noqa: F821
        #         _chainId_: "uint256" = chain.id  # noqa: F821
        #         _verifyingContract_: "address" = swap.address  # noqa: F821
        #
        #         # EIP-2612 Data Fields
        #         owner: "address"  # noqa: F821
        #         spender: "address"  # noqa: F821
        #         value: "uint256"  # noqa: F821
        #         nonce: "uint256"  # noqa: F821
        #         deadline: "uint256" = 2 ** 256 - 1  # noqa: F821
        #
        #     permit = Permit(owner=alice.address, spender=bob.address, value=2 ** 256 - 1, nonce=0)
        #     sig = alice.sign_message(permit)
        #
        #     tx = swap.permit(
        #         mock_contract, bob, 2 ** 256 - 1, 2 ** 256 - 1, sig.v, sig.r, sig.s, {"from": bob}
        #     )
        #
        #     # make sure this is hit when owner is a contract
        #     assert tx.subcalls[-1]["function"] == "isValidSignature(bytes32,bytes)"
