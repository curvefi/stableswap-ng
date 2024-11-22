# Stableswap NG

Permissionless deployment of Curve Stableswap plain and metapools. Supports up to 8 coins for plain pools and 2 coins for metapools. Supports: rate-oraclised tokens (e.g. wstETH), ERC4626 (sDAI), rebasing (stETH), and plain (WETH:stETH) pools. Does not support native tokens.

For integrators: check exchange_received. That should improve your pathing significantly. Be aware that if a pool contains rebasing tokens, this method is intentionally disabled.

# Deployments

For a full list of deployments, please check: [The deployment script](scripts/deploy_infra.py)

## Overview

The metapool factory has several core components:

- [`Factory`](contracts/main/CurveStableSwapFactoryNG.vy) is the main contract used to deploy new metapools. It also acts a registry for finding the deployed pools and querying information about them.
- New pools are deployed via blueprints. The [implementation contract](contracts/main/CurveStableSwapNG.vy) targeted by the proxy is determined according to the base pool.

See the [documentation](https://docs.curve.fi) for more detailed information.

## Testing

### Installation

Install dependencies using poetry (python ^3.10.4)

```shell
pip install poetry==1.8.3
poetry install
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
