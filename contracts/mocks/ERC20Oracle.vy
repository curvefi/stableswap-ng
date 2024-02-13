# pragma version 0.3.10

"""
@notice Mock ERC20 with oracle
@dev This is for testing only, it is NOT safe for use
"""


event Transfer:
    _from: indexed(address)
    _to: indexed(address)
    _value: uint256


event Approval:
    _owner: indexed(address)
    _spender: indexed(address)
    _value: uint256


name: public(String[64])
symbol: public(String[32])
decimals: public(uint256)
balanceOf: public(HashMap[address, uint256])
allowances: HashMap[address, HashMap[address, uint256]]
totalSupply: public(uint256)

exchange_rate: public(uint256)

# asset type
asset_type: public(constant(uint8)) = 1


@external
def __init__(
    _name: String[64],
    _symbol: String[32],
    _decimals: uint256,
    _exchange_rate: uint256
):

    self.name = _name
    self.symbol = _symbol

    assert _decimals == 18, "Decimals must be 18"
    self.decimals = _decimals
    self.exchange_rate = _exchange_rate


@external
@view
def allowance(_owner: address, _spender: address) -> uint256:
    return self.allowances[_owner][_spender]


@external
def transfer(_to: address, _value: uint256) -> bool:
    self.balanceOf[msg.sender] -= _value
    self.balanceOf[_to] += _value
    log Transfer(msg.sender, _to, _value)
    return True


@external
def transferFrom(_from: address, _to: address, _value: uint256) -> bool:
    self.balanceOf[_from] -= _value
    self.balanceOf[_to] += _value
    self.allowances[_from][msg.sender] -= _value
    log Transfer(_from, _to, _value)
    return True


@external
def approve(_spender: address, _value: uint256) -> bool:
    self.allowances[msg.sender][_spender] = _value
    log Approval(msg.sender, _spender, _value)
    return True


@external
@view
def exchangeRate() -> uint256:
    rate: uint256 = self.exchange_rate
    return rate


@external
def set_exchange_rate(rate: uint256) -> bool:
    self.exchange_rate = rate
    return True


@external
def _mint_for_testing(_target: address, _value: uint256) -> bool:
    self.totalSupply += _value
    self.balanceOf[_target] += _value
    log Transfer(empty(address), _target, _value)

    return True
