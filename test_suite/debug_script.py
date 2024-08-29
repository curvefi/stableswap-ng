import pytest

def main():
    # Pytest arguments
    pytest_args = [
        '-s',  # Do not capture output, allowing you to see print statements and debug info
        'tests/gauge/test_rewards.py::test_set_rewards_no_deposit',  # Specific test to run
        '--maxfail=1',  # Stop after the first failure
        '--tb=short'    # Shorter traceback for easier reading
    ]

    # Run pytest with the specified arguments
    pytest.main(pytest_args)

if __name__ == "__main__":
    main()