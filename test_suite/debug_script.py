import pytest
import sys


def is_debug_mode():
    return sys.gettrace() is not None


def main():
    # Pytest arguments
    pytest_args = [
        "-s",  # Do not capture output, allowing you to see print statements and debug info
        "tests/pools/liquidity/test_remove_liquidity.py::test_remove_liquidity",  # Specific test to run
        # '--maxfail=1',  # Stop after the first failure
        "--tb=short",  # Shorter traceback for easier reading
        "-rA",  # Show extra test summary info
    ]

    if not is_debug_mode():
        pass
        pytest_args.append("-n=auto")  # Automatically determine the number of workers

    # Run pytest with the specified arguments
    pytest.main(pytest_args)


if __name__ == "__main__":
    main()
