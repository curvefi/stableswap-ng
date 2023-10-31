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

## Ethereum

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0x20D1c021525C85D9617Ccc64D8f547d5f730118A](https://etherscan.io/address/0x20D1c021525C85D9617Ccc64D8f547d5f730118A#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x87DD13Dd25a1DBde0E1EdcF5B8Fa6cfff7eABCaD](https://etherscan.io/address/0x87DD13Dd25a1DBde0E1EdcF5B8Fa6cfff7eABCaD#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0x3E3B5F27bbf5CC967E074b70E9f4046e31663181](https://etherscan.io/address/0x3E3B5F27bbf5CC967E074b70E9f4046e31663181#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [0x19bd1AB34d6ABB584b9C1D5519093bfAA7f6c7d2](https://etherscan.io/address/0x19bd1AB34d6ABB584b9C1D5519093bfAA7f6c7d2#code)
5. [`LiquidityGauge`](contracts/main/LiquidityGauge.vy): [0xF5617D4f7514bE35fce829a1C19AE7f6c9106979](https://etherscan.io/address/0xF5617D4f7514bE35fce829a1C19AE7f6c9106979#code)
6. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0x6A8cbed756804B16E05E741eDaBd5cB544AE21bf](https://etherscan.io/address/0x6A8cbed756804B16E05E741eDaBd5cB544AE21bf#code)

## Gnosis

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0x87FE17697D0f14A222e8bEf386a0860eCffDD617](https://gnosisscan.io/address/0x87FE17697D0f14A222e8bEf386a0860eCffDD617#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x5eeE3091f747E60a045a2E715a4c71e600e31F6E](https://gnosisscan.io/address/0x5eeE3091f747E60a045a2E715a4c71e600e31F6E#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0xd2002373543Ce3527023C75e7518C274A51ce712](https://gnosisscan.io/address/0xd2002373543Ce3527023C75e7518C274A51ce712#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [](https://gnosisscan.io/address/#code)
5. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8](https://gnosisscan.io/address/0xbC0797015fcFc47d9C1856639CaE50D0e69FbEE8#code)

## Arbitrum

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0x3d6cB2F6DcF47CDd9C13E4e3beAe9af041d8796a](https://arbiscan.io/address/0x3d6cB2F6DcF47CDd9C13E4e3beAe9af041d8796a#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0xC1b393EfEF38140662b91441C6710Aa704973228](https://arbiscan.io/address/0xC1b393EfEF38140662b91441C6710Aa704973228#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0x76303e4fDcA0AbF28aB3ee42Ce086E6503431F1D](https://arbiscan.io/address/0x76303e4fDcA0AbF28aB3ee42Ce086E6503431F1D#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [0xd125E7a0cEddF89c6473412d85835450897be6Dc](https://arbiscan.io/address/0xd125E7a0cEddF89c6473412d85835450897be6Dc#code)
5. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0x9AF14D26075f142eb3F292D5065EB3faa646167b](https://arbiscan.io/address/0x9AF14D26075f142eb3F292D5065EB3faa646167b#code)

## Optimism

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6](https://optimistic.etherscan.io/address/0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x506F594ceb4E33F5161139bAe3Ee911014df9f7f](https://optimistic.etherscan.io/address/0x506F594ceb4E33F5161139bAe3Ee911014df9f7f#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0x87FE17697D0f14A222e8bEf386a0860eCffDD617](https://optimistic.etherscan.io/address/0x87FE17697D0f14A222e8bEf386a0860eCffDD617#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [0x1764ee18e8B3ccA4787249Ceb249356192594585](https://optimistic.etherscan.io/address/0x1764ee18e8B3ccA4787249Ceb249356192594585#code)
5. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0x5eeE3091f747E60a045a2E715a4c71e600e31F6E](https://optimistic.etherscan.io/address/0x5eeE3091f747E60a045a2E715a4c71e600e31F6E#code)

## Polygon

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0xf3A431008396df8A8b2DF492C913706BDB0874ef](https://polygonscan.com/address/0xf3A431008396df8A8b2DF492C913706BDB0874ef#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6](https://polygonscan.com/address/0x8b3EFBEfa6eD222077455d6f0DCdA3bF4f3F57A6#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0x506F594ceb4E33F5161139bAe3Ee911014df9f7f](https://polygonscan.com/address/0x506F594ceb4E33F5161139bAe3Ee911014df9f7f#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [0x87FE17697D0f14A222e8bEf386a0860eCffDD617](https://polygonscan.com/address/0x87FE17697D0f14A222e8bEf386a0860eCffDD617#code)
5. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0x1764ee18e8B3ccA4787249Ceb249356192594585](https://polygonscan.com/address/0x1764ee18e8B3ccA4787249Ceb249356192594585#code)

## Base

1. [`CurveStableSwapNGMath`](contracts/main/CurveStableSwapNGMath.vy): [0x506F594ceb4E33F5161139bAe3Ee911014df9f7f](https://basescan.org/address/0x506F594ceb4E33F5161139bAe3Ee911014df9f7f#code)
2. [`CurveStableSwapNGViews`](contracts/main/CurveStableSwapNGViews.vy): [0x87FE17697D0f14A222e8bEf386a0860eCffDD617](https://basescan.org/address/0x87FE17697D0f14A222e8bEf386a0860eCffDD617#code)
3. [`StableSwapNG`](contracts/main/CurveStableSwapNG.vy): [0x1764ee18e8B3ccA4787249Ceb249356192594585](https://basescan.org/address/0x1764ee18e8B3ccA4787249Ceb249356192594585#code)
4. [`StableSwapMetaNG`](contracts/main/CurveStableSwapMetaNG.vy): [0x5eee3091f747e60a045a2e715a4c71e600e31f6e](https://basescan.org/address/0x5eee3091f747e60a045a2e715a4c71e600e31f6e#code)
5. [`CurveStableSwapFactoryNG`](contracts/main/CurveStableSwapFactoryNG.vy): [0xd2002373543Ce3527023C75e7518C274A51ce712](https://basescan.org/address/0xd2002373543Ce3527023C75e7518C274A51ce712#code)

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
