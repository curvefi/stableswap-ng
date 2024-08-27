import pytest

def main():
    # Pytest arguments
    pytest_args = [
        '-s',  # Do not capture output, allowing you to see print statements and debug info
        'tests/token/test_token_transfer_from.py::test_transfer_event_fires',  # Specific test to run
        '--maxfail=1',  # Stop after the first failure
        '--tb=short'    # Shorter traceback for easier reading
    ]

    # Run pytest with the specified arguments
    pytest.main(pytest_args)

if __name__ == "__main__":
    main()