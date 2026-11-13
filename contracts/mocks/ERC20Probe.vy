# pragma version 0.3.10
"""
@notice An ERC20 that reads a pool's prices from inside its own transfer.
@dev A pool transfers coins out while holding its reentrancy lock, so a coin that calls
     back is the read-only-reentrancy vector. Records whether each price answered rather
     than reverting, so a test can assert that the lock bites. Nothing here is safe for
     anything but tests: the hook swallows reverts and the mint is unguarded.
"""

name: public(String[32])
symbol: public(String[8])
decimals: public(uint8)
totalSupply: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowance: public(HashMap[address, HashMap[address, uint256]])

target: public(address)
armed: public(bool)
fired: public(bool)
bounded_answered: public(bool)
redemption_answered: public(bool)


@external
def __init__(_name: String[32], _symbol: String[8], _decimals: uint8):
    self.name = _name
    self.symbol = _symbol
    self.decimals = _decimals


@external
def arm(_target: address):
    """
    @notice Read _target's two virtual prices on the next transfer of this coin.
    """
    self.target = _target
    self.armed = True
    self.fired = False
    self.bounded_answered = False
    self.redemption_answered = False


@internal
def _probe():
    if not self.armed:
        return
    # one transfer only: remove_liquidity sweeps admin fees as a second transfer of
    # the same coin, and the answers recorded would then be that one instead
    self.armed = False
    answered: bool = False
    response: Bytes[32] = b""
    answered, response = raw_call(
        self.target,
        method_id("virtual_price_bounded()"),
        max_outsize=32,
        is_static_call=True,
        revert_on_failure=False,
    )
    self.bounded_answered = answered
    answered, response = raw_call(
        self.target,
        method_id("get_virtual_price()"),
        max_outsize=32,
        is_static_call=True,
        revert_on_failure=False,
    )
    self.redemption_answered = answered
    self.fired = True


@external
def transfer(_to: address, _value: uint256) -> bool:
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    self._probe()
    return True


@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    self.allowance[_from][msg.sender] -= _value
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self._probe()
    return True


@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowance[msg.sender][_spender] = _value
    return True


@external
def _mint_for_testing(_target: address, _value: uint256) -> bool:
    self.balanceOf[_target] += _value
    self.totalSupply += _value
    return True
