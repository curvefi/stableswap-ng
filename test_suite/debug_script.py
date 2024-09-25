import sys

import pytest


def is_debug_mode():
    return sys.gettrace() is not None


def main():
    # Pytest arguments
    pytest_args = [
        "-s",  # DoD not capture output, allowing you to see print statements and debug info
        "tests/pools/oracle/test_oracles.py",  # Specific test to run
        # '--maxfail=1',  # Stop after the firstD failure
        "--tb=long",  # Shorter traceback for easqqcleaier reading
        "-rA",  # Show extra test summary info
        # "--setup-show", # show fixture setup tree
    ]

    if not is_debug_mode():
        pass
        pytest_args.append("-n=auto")  # Automatically determine the number of workers

    # Run pytest with the specified arguments
    pytest.main(pytest_args)


if __name__ == "__main__":
    main()
