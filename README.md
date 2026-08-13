# Stableswap NG

Permissionless deployment of Curve Stableswap plain and metapools. Supports up to 8 coins for plain pools and 2 coins for metapools. Supports: rate-oraclised tokens (e.g. wstETH), ERC4626 (sDAI), rebasing (stETH), and plain (WETH:stETH) pools. Does not support native tokens.

For integrators: check exchange_received. That should improve your pathing significantly. Be aware that if a pool contains rebasing tokens, this method is intentionally disabled.

# Deployments

For a full list of deployments, please check: [The deployment script](scripts/deploy_infra.py)

## Overview

The metapool factory has several core components:

- [`Factory`](contracts/main/CurveStableSwapFactoryNG.vy) is the main contract used to deploy new metapools. It also acts a registry for finding the deployed pools and querying information about them.
- New pools are deployed via blueprints. The [implementation contract](contracts/main/CurveStableSwapNG.vy) targeted by the proxy is determined according to the base pool.
- There is extra StableSwap implementation with admin functionality on [`admin-implementation`](https://github.com/curvefi/stableswap-ng/tree/admin-implementation) branch initially used by *crosscurve* on *Sonic*.

See the [documentation](https://docs.curve.fi) for more detailed information.

## Library usage

Install the repository as a Python package, then import the LP oracle from Vyper:

```vyper
from stableswap_ng import LPOracle
```

## Testing

### Installation

Install dependencies using uv (python >=3.10)

```shell
uv sync --group dev
```

The contracts in this repository use Vyper 0.3.10, while the packaged LP oracle
uses Vyper 0.4.3. Run the legacy contract tests in their locked environment:

```shell
uv run --python 3.10 --no-project --with-requirements requirements-tests.txt pytest tests/
```

### Type of tests

Testing gauge

```shell
pytest tests/gauge/
```

Testing factory

```shell
pytest tests/factory/
```

Testing swap is ERC20

```shell
pytest tests/token/
```

Testing swaps

```shell
pytest tests/pools/
```
