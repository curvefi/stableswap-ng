"""
Plot liquidity density vs AMM price for a 2-coin Curve Stableswap pool.

Definitions (all magnitudes, taken as positive):
    p   = dx/dy                              (marginal price of Y in units of X)
    rho = (dp/p) / (dx/(x + p*y))            (relative price impact)
        = (x + p*y) * (dp/dx) / p
    L   = 1 / rho                            (liquidity density)

Invariant (n-coin Stableswap, n=2 here):
    A * n^n * (x + y) + D = A * D * n^n + D^(n+1) / (n^n * x * y)

For n=2:
    f(x, y) = 4A(x + y) + D - 4AD - D^3/(4 x y) = 0

Differentiating along the invariant:
    df/dx = 4A + D^3 / (4 x^2 y)
    df/dy = 4A + D^3 / (4 x y^2)
    dx/dy = -df/dy / df/dx        (sign convention; we plot |dx/dy|)

Note: the on-chain `A` field equals A_math * A_PRECISION (A_PRECISION = 100).
This script uses mathematical A directly.
"""

import numpy as np
import matplotlib.pyplot as plt


def get_y(A: float, D: float, x: np.ndarray, n: int = 2) -> np.ndarray:
    """Solve the n-coin Stableswap invariant for y given x. n=2 reduces to a quadratic."""
    Ann = A * n**n
    S = x          # sum of all balances except y
    P = x          # product of all balances except y (n=2)
    b = S + D / Ann
    c = D ** (n + 1) / (n**n * P * Ann)
    # y^2 + (b - D) y - c = 0
    disc = (b - D) ** 2 + 4 * c
    return (-(b - D) + np.sqrt(disc)) / 2


def liquidity_density(A: float, D: float, x: np.ndarray, n: int = 2):
    """Return (price p, density L) along the invariant, parameterized by x."""
    y = get_y(A, D, x, n)
    Ann = A * n**n
    prod = x * y  # n=2

    df_dx = Ann + D ** (n + 1) / (n**n * x * prod)
    df_dy = Ann + D ** (n + 1) / (n**n * y * prod)
    p = df_dy / df_dx                  # |dx/dy|

    # dp/dx along the invariant — analytic, so we don't rely on a sampled grid.
    # Let g = D^(n+1) / (n^n * x * y * prod) = D^(n+1) / (n^n * (x y)^2) for n=2,
    # but it's cleaner to expand:
    #   df_dx = Ann + D^3 / (4 x^2 y),  df_dy = Ann + D^3 / (4 x y^2)
    # dy/dx = -df_dx / df_dy.
    # Then differentiate p = df_dy / df_dx w.r.t. x using y = y(x).
    K = D ** 3 / 4.0
    a_x = Ann + K / (x**2 * y)
    a_y = Ann + K / (x * y**2)
    dy_dx = -a_x / a_y

    da_x_dx = -2 * K / (x**3 * y) - (K / (x**2 * y**2)) * dy_dx
    da_y_dx = -(K / (x**2 * y**2)) - 2 * (K / (x * y**3)) * dy_dx

    dp_dx = (da_y_dx * a_x - a_y * da_x_dx) / a_x**2

    rho = (x + p * y) * dp_dx / p
    L = 1.0 / np.abs(rho)
    return p, L


def main():
    D = 200.0  # total nominal liquidity (x + y at peg)
    A_values = [1, 2, 3, 4, 5]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # Sweep x across most of [0, D]; avoid endpoints where y -> 0/inf.
    x = np.linspace(D * 5e-4, D * (1 - 5e-4), 4000)

    for A in A_values:
        p, L = liquidity_density(A, D, x)
        ax1.plot(p, L, label=f"A = {A}")
        ax2.plot(p, L, label=f"A = {A}")

    # Constant-product baseline: L = 1/4 everywhere (Uniswap V2).
    for ax in (ax1, ax2):
        ax.axhline(0.25, color="gray", linestyle="--", linewidth=1,
                   label="Uniswap V2 (L = 1/4)")
        ax.set_xlabel("price  p = dx/dy")
        ax.set_ylabel("liquidity density  L = 1 / [(x + p y) (dp/dx) / p]")
        ax.grid(True, which="both", alpha=0.3)
        ax.legend()

    ax1.set_title("Linear price axis")
    ax1.set_xlim(0, 3)
    ax1.set_yscale("log")

    ax2.set_title("Log price axis")
    ax2.set_xscale("log")
    ax2.set_yscale("log")

    fig.suptitle("Curve Stableswap (n=2): liquidity density vs price", y=1.02)
    fig.tight_layout()

    out = "liquidity_density.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    print(f"saved {out}")
    plt.show()


if __name__ == "__main__":
    main()
