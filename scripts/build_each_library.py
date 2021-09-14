#!/usr/bin/env python3
import argparse
import glob
import json
import os
import subprocess
import typing

import junitparser


class LibraryTestSuite:
    def __init__(self, report: junitparser.JUnitXml, name: str, version: str):
        self.report = report
        self.test_suite = junitparser.TestSuite(name)
        self.test_suite.add_property('version', version)
        self.name = name
        self.version = version

    def __enter__(self):
        print(f'::group::Checking {self.name}@{self.version}...')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.report.add_testsuite(self.test_suite)


class LibraryTestCase:
    def __init__(self, test_suite: LibraryTestSuite, name: str):
        self.name = name
        self.test_suite = test_suite
        self.failed = False

    def __enter__(self):
        print(f"Test: {self.name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f"Test {self.name} finished: {str(exc_type) if exc_type else 'Success'}")
        test_case = junitparser.TestCase(self.name)
        if exc_type is not None:
            test_case.result = [junitparser.Failure()]
            self.failed = True
        self.test_suite.test_suite.add_testcase(test_case)
        if exc_type in [subprocess.CalledProcessError, RuntimeError]:
            return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        required=True,
        type=argparse.FileType('r'),
        help="JSON file with the list of libraries"
    )
    parser.add_argument(
        "--config-file",
        type=str,
        help="arduino-cli config file"
    )
    parser.add_argument(
        "--library-dir",
        type=str,
        required=True,
        help="arduino library directory"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="output xUnit file name"
    )
    args = parser.parse_args()

    arduino_cli_cmd = [
        "arduino-cli"
    ]
    if args.config_file:
        arduino_cli_cmd += [
            "--config-file",
            args.config_file
        ]

    libraries = json.load(args.input)

    report = junitparser.JUnitXml()

    for lib in libraries:
        test_single_lib(arduino_cli_cmd, lib, report, args.library_dir)

    report.write(args.output)


def test_single_lib(arduino_cli_cmd: typing.List[str], lib: dict, report: junitparser.JUnitXml, library_dir: str):
    name = lib["name"]
    version = lib["version"]
    lib_spec = f"{name}@{version}"
    with LibraryTestSuite(report, name, version) as lts:
        with LibraryTestCase(lts, "Install library") as ltc:
            install_library(arduino_cli_cmd, lib_spec)
            lib_dir = os.path.join(library_dir, name.replace(' ', '_'))
            if not os.path.exists(lib_dir):
                raise RuntimeError(f"Failed to find library dir ({lib_dir})")

        if ltc.failed:
            return

        provided_headers = lib.get("providesIncludes", [])
        if provided_headers:
            with LibraryTestCase(lts, "Compile with provided headers"):
                build_test_sketch(arduino_cli_cmd, provided_headers)
        else:
            headers = glob.glob(os.path.join(lib_dir, "*.h"))
            if not headers:
                headers = glob.glob(os.path.join(lib_dir, 'src', '*.h'))
            if headers:
                with LibraryTestCase(lts, "Compile with discovered headers"):
                    build_test_sketch(arduino_cli_cmd, headers)


def install_library(arduino_cli_cmd: typing.List[str], lib_spec: str):
    subprocess.check_call(arduino_cli_cmd + [
        "lib", "install", lib_spec
    ], stderr=subprocess.STDOUT)


def build_sketch(arduino_cli_cmd: typing.List[str], path: str):
    board_spec = ["-b", "esp32:esp32:esp32"]
    subprocess.check_call(arduino_cli_cmd + [
        "compile", *board_spec, path
    ], stderr=subprocess.STDOUT)


def build_test_sketch(arduino_cli_cmd: typing.List[str], headers: typing.List[str]):
    if not os.path.exists("test"):
        os.mkdir("test")
    with open(os.path.join("test", "test.ino"), "w") as sketch:
        for header in headers:
            header_name = os.path.basename(header)
            print(f"#include <{header_name}>", file=sketch)
        print("void setup(){}", file=sketch)
        print("void loop(){}", file=sketch)
    build_sketch(arduino_cli_cmd, os.path.join(os.getcwd(), "test"))


if __name__ == "__main__":
    main()
