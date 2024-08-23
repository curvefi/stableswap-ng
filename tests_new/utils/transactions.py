from typing import Any

# from boa.vyper.contract import VyperContract, VyperFunction
# from boa.vyper.event import Event

from boa.contracts.vyper.vyper_contract import VyperContract, VyperFunction
from boa.contracts.vyper.event import Event

def call_returning_result_and_logs(
    contract: VyperContract, function_name: str, *args, value=0, gas=None, sender=None, **kwargs
) -> tuple[Any, list[Event]]:
    func: VyperFunction = getattr(contract, function_name)
    calldata_bytes = func.prepare_calldata(*args, **kwargs)
    override_bytecode = getattr(func, "override_bytecode", None)

    with func.contract._anchor_source_map(func._source_map):
        computation = func.env.execute_code(
            to_address=func.contract.address,
            sender=sender,
            data=calldata_bytes,
            value=value,
            gas=gas,
            is_modifying=func.func_t.is_mutable,
            override_bytecode=override_bytecode,
            contract=func.contract,
        )

        typ = func.func_t.return_type
        res = func.contract.marshal_to_python(computation, typ)

        events = contract.get_logs(computation)

    return res, events
