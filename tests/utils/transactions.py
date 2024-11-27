from typing import Any

from boa.contracts.vyper.event import Event
from boa.contracts.vyper.vyper_contract import VyperContract


def call_returning_result_and_logs(
    # rewrite for boa 0.1.10, where _computation is preserved after function call,
    # allowing access to events
    contract: VyperContract,
    function_name: str,
    *args,
    value=0,
    gas=None,
    sender=None,
    **kwargs,
) -> tuple[Any, list[Event]]:
    function_handle = getattr(contract, function_name)
    res = function_handle(*args, value=value, gas=gas, sender=sender, **kwargs)
    events = contract.get_logs()

    return res, events
