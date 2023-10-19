# Stableswap NG

Permissionless deployment of Curve Stableswap plain and metapools. Supports up to 8 coins for plain pools and 2 coins for metapools. Supports: rate-oraclised tokens (e.g. wstETH), ERC4626 (sDAI), rebasing (stETH), and plain (WETH:stETH) pools. Does not support native tokens.

For integrators: check exchange_received. That should improve your pathing significantly. Be aware that if a pool contains rebasing tokens, this method is intentionally disabled.

# Deployments

## Sepolia

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0xbc7654d2dd901aaaa3be4cb5bc0f10dea9f96443](https://sepolia.etherscan.io/address/0xbc7654d2dd901aaaa3be4cb5bc0f10dea9f96443#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x07920e98a66e462c2aa4c8fa6200bc68ca161ea0](https://sepolia.etherscan.io/address/0x07920e98a66e462c2aa4c8fa6200bc68ca161ea0#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0x296d2b5c23833a70d07c8fcbb97d846c1ff90ddd](https://sepolia.etherscan.io/address/0x296d2b5c23833a70d07c8fcbb97d846c1ff90ddd#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [](https://sepolia.etherscan.io/address/#code)
5. [`LiquidityGauge`](contracts/main/LiquidityGauge.vy): [0x64891ab20392a029c0f231656ff13c5ee64b730c](https://sepolia.etherscan.io/address/0x64891ab20392a029c0f231656ff13c5ee64b730c#code)
6. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0xfb37b8D939FFa77114005e61CFc2e543d6F49A81](https://sepolia.etherscan.io/address/0xfb37b8D939FFa77114005e61CFc2e543d6F49A81#code)

## Gnosis

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0x87FE17697D0f14A222e8bEf386a0860eCffDD617](https://gnosisscan.io/address/0x87FE17697D0f14A222e8bEf386a0860eCffDD617#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x5eeE3091f747E60a045a2E715a4c71e600e31F6E](https://gnosisscan.io/address/0x5eeE3091f747E60a045a2E715a4c71e600e31F6E#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0xd2002373543Ce3527023C75e7518C274A51ce712](https://gnosisscan.io/address/0xd2002373543Ce3527023C75e7518C274A51ce712#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [](https://gnosisscan.io/address/#code)
5. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8](https://gnosisscan.io/address/0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8#code)

## Overview

The metapool factory has several core components:

- [`Factory`](contracts/main/CurveStableSwapFactoryNG.vy) is the main contract used to deploy new metapools. It also acts a registry for finding the deployed pools and querying information about them.
- New pools are deployed via blueprints. The [implementation contract](contracts/main/CurveStableSwapNG.vy) targetted by the proxy is determined according to the base pool.

See the [documentation](https://curve.readthedocs.io) for more detailed information.

## Testing

### Installation

Install dependencies using poetry (python ^3.10.4)

```shell
pip install poetry==1.5.1
poetry install
```

### Paramaters

- `--pool-size` - size of pool (N_COINS), available parameters: `[2]`
- `--pool-type` - type of pool, available parameters: `[basic,meta]`
- `--token-types` - token types to test against(divided by comma), available parameters: `[plain,eth,oracle,rebasing]`
- `--decimals` - token decimals (divided by comma), default `18,18`
- `--return-types` - types of .transfer() returns to test against (divided by comma), default `revert,False,None`

### Type of tests

Testing gauge

```shell
pytest tests/gauge/
```

Testing factory

```shell
pytest tests/test_factory.py
```

Testing swap is ERC20

```shell
pytest tests/test_token.py
```

Testing swaps

```shell
pytest tests/pools/
```
