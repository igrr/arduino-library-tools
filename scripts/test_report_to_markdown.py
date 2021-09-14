#!/usr/bin/env python3

import argparse
import sys

import junitparser
import tabulate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, required=True, help="Input xUnit test report file")
    parser.add_argument("--output", type=argparse.FileType('w'), help="Output markdown file")
    args = parser.parse_args()

    report = junitparser.JUnitXml.fromfile(args.input)
    table_headers = ["Library", "Version", "Status", "Passed", "Failed"]
    table = []
    total_install_failed = 0
    total_failed = 0
    total_passed = 0
    for ts in report:  # type: junitparser.TestSuite
        version = "unknown"
        for p in ts.properties():
            if p.name == "version":
                version = p.value
                break

        if ts.tests == ts.errors + ts.failures:
            status = ':stop_sign: Failed to install'
            passed = 0
            failed = 1
            total_install_failed += 1
        elif ts.errors or ts.failures:
            status = ':warning: Failed'
            failed = ts.errors + ts.failures
            passed = ts.tests - failed - 1
            total_failed += 1
        else:
            status = ':white_check_mark: OK'
            passed = ts.tests
            failed = 0
            total_passed += 1

        table.append([
            ts.name,
            version,
            status,
            passed,
            failed
        ])

    def sort_fn(row):
        return row[2] + row[0].lower()

    table = sorted(table, key=sort_fn)

    out = args.output or sys.stdout
    print("# Summary", file=out)
    print(tabulate.tabulate([[str(total_passed), str(total_failed), str(total_install_failed)]],
                            headers=["OK", "Failed", "Failed to install"], tablefmt='github'), file=out)
    print("# Details", file=out)
    print(tabulate.tabulate(table, table_headers, tablefmt='github'), file=out)


if __name__ == "__main__":
    main()
