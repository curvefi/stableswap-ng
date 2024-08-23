import os
import subprocess
from datetime import datetime

# Script to run all tests in the tests directory and save the output to a timestamped folder
# Please run it from project root directory

# Base directories
tests_base_dir = "tests"
reports_base_dir = "test_suite/test_reports"
skip_subfolders = ["__pycache__", "utils", "fixtures"]

only_subfolders = ["factory"]

tests_to_run = [
    'test_factory_add_pools'
]

# Function to run pytest for each file and save output to folder corresponding to the file
def run_tests_and_save_output():
    # Get timestamp for the script run (same for all tests)
    timestamp = datetime.now().strftime("%d%m%y_%H%M%S")

    for root, dirs, files in os.walk(tests_base_dir):
        # Skip __pycache__ directories
        dirs[:] = [d for d in dirs if d not in skip_subfolders]
        if len(only_subfolders) > 0:
            dirs[:] = [d for d in dirs if d in only_subfolders]
        for file in files:
            if file.startswith("test_") and file.endswith(".py"):
                if len(only_subfolders) == 0 and len(tests_to_run) > 0:
                    if file not in tests_to_run and file.strip('.py') not in tests_to_run:
                        continue
                # Construct paths
                relative_path = os.path.relpath(root, start=tests_base_dir)
                test_file_path = os.path.join(root, file)
                report_dir = os.path.join(reports_base_dir, relative_path, file.replace('.py', ''))
                
                # Create a folder for the test output
                os.makedirs(report_dir, exist_ok=True)
                
                # Run pytest and save output
                output_file = os.path.join(report_dir, timestamp+".log")
                command = f"pytest {test_file_path} -n auto | tee {output_file}"
                print(f"Running {test_file_path}")
                subprocess.run(command, shell=True, check=True)

# Main function
def main():
    run_tests_and_save_output()

if __name__ == "__main__":
    if 'test_suite' in os.getcwd():
        os.chdir('..')
        print(f"Changed directory to {os.getcwd()}")

    main()