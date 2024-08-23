import os
import re
import pandas as pd
from tabulate import tabulate

# Base directory for reports
reports_base_dir = "test_suite/test_reports"

# Individual regex patterns to match each possible status
failed_pattern = re.compile(r"(\d+)\s+failed")
passed_pattern = re.compile(r"(\d+)\s+passed")
skipped_pattern = re.compile(r"(\d+)\s+skipped")
deselected_pattern = re.compile(r"(\d+)\s+deselected")
xfailed_pattern = re.compile(r"(\d+)\s+xfailed")
warnings_pattern = re.compile(r"(\d+)\s+warnings")
errors_pattern = re.compile(r"(\d+)\s+errors")
time_pattern = re.compile(r"in\s+([\d.]+)s")

# keywords = ["failed", "passed", "skipped", "deselected", "xfailed", "warnings", "errors", "time"]
# Enforcing the line format with ===== symbols
line_format_pattern = re.compile(r"={5,}")

def extract_summary(line):
    if not line_format_pattern.search(line):
        return None

    failed = failed_pattern.search(line)
    passed = passed_pattern.search(line)
    skipped = skipped_pattern.search(line)
    deselected = deselected_pattern.search(line)
    xfailed = xfailed_pattern.search(line)
    warnings = warnings_pattern.search(line)
    errors = errors_pattern.search(line)
    time_taken = time_pattern.search(line)

    # Extract values or default to "0"
    failed = int(failed.group(1)) if failed else 0
    passed = int(passed.group(1)) if passed else 0
    skipped = int(skipped.group(1)) if skipped else 0
    deselected = int(deselected.group(1)) if deselected else 0
    xfailed = int(xfailed.group(1)) if xfailed else 0
    warnings = int(warnings.group(1)) if warnings else 0
    errors = int(errors.group(1)) if errors else 0
    time_taken = float(time_taken.group(1)) if time_taken else 0.0

    total = sum([failed, passed, skipped, deselected, xfailed, warnings, errors])
    
    if total == 0:
        return None

    return failed, passed, skipped, deselected, xfailed, warnings, errors, time_taken

# Function to traverse and generate the report
def generate_report():
    data = []  # List to store data for DataFrame
    for root, dirs, files in os.walk(reports_base_dir):
        if files:
            for file in files:
                if file.endswith(".log"):
                    log_file_path = os.path.join(root, file)
                    with open(log_file_path, 'r') as f:
                        for line in f:
                            summary = extract_summary(line)

                            if summary:
                                failed, passed, skipped, deselected, xfailed, warnings, errors, time_taken = summary
                                total = int(sum(summary) - time_taken)
                                # Extract folder, subfolder, filename, and timestamp
                                relative_path = os.path.relpath(root, start=reports_base_dir)
                                timestamp = file.replace('.log', '')

                                # Append data to the list
                                data.append({
                                    "Test": relative_path,
                                    "Timestamp": timestamp,
                                    "PASS": passed,
                                    "FAIL": failed,
                                    "ERRORS": errors,
                                    "SKIP": skipped,
                                    "XFAILED": xfailed,
                                    "WARNINGS": warnings,
                                    "TOTAL": total,
                                    "TIME": time_taken
                                })

    # Convert list to DataFrame
    df = pd.DataFrame(data)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 120)  

    # print(df)
    # Convert the 'Timestamp' to a datetime object for accurate comparison (if needed)
    df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%d%m%y_%H%M%S')

    # Group by 'Path' and then find the row with the latest 'Timestamp' in each group
    latest_timestamps = df.loc[df.groupby('Test')['Timestamp'].idxmax()]

    # Exclude the 'Timestamp' column from the final DataFrame
    latest_tests = latest_timestamps.drop('Timestamp', axis=1)

    # # Sort the DataFrame
    latest_tests = latest_tests.sort_values('TOTAL', ascending=False)
    
    # # Display the resulting DataFrame with only the latest timestamp for each Path
    # print(latest_tests)
    print(latest_tests.to_string(index=False, justify='right'))

    # # Save the DataFrame to an ascii table
    with open('test_suite/latest_report.txt', 'w') as f:
        f.write(tabulate(latest_tests, headers='keys', tablefmt='psql'))

def main():
    # Run the report generation
    generate_report()

if __name__ == "__main__":
    main()
