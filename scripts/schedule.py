#!/usr/bin/env python3
import argparse
import textwrap
import json
import typing
import collections
import packaging.version
import os


def library_arch_matches(library_dict: typing.Dict, arch_list: typing.List[str]) -> bool:
    if not arch_list:
        return True
    if "architectures" not in library_dict:
        return False
    return any([arch in arch_list for arch in library_dict["architectures"]])


def main():
    parser = argparse.ArgumentParser(description=textwrap.dedent("""
        This script reads the list of Arduino libraries from the specified file,
        picks the latest version of each library, and outputs the resulting list.
        The list is optionally split into multiple lists, for one list per file. 
    """))
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Split the list of libraries into given number of files"
    )
    parser.add_argument(
        "--arch",
        type=str,
        nargs='+',
        help="List of architectures which should be included"
    )
    parser.add_argument(
        "--input",
        required=True,
        type=argparse.FileType('r'),
        help="JSON file with the list of libraries"
    )
    parser.add_argument(
        "--output",
        type=str,
        required=True,
        help="Output file name. Integer index will be added to the name if --parallel argument is given."
    )
    args = parser.parse_args()

    input_json = json.load(args.input)
    if isinstance(input_json, dict):
        libraries_list = input_json["libraries"]
    elif isinstance(input_json, list):
        libraries_list = input_json
    else:
        raise NotImplementedError()

    library_versions: typing.Dict[str, typing.List] = collections.defaultdict(list)
    for lib in libraries_list:
        if not library_arch_matches(lib, args.arch):
            continue
        library_versions[lib["name"]].append(lib)

    selected_libraries = list()
    for name, version_list in library_versions.items():
        latest_version = None
        latest_version_lib = None
        for lib in version_list:
            ver = packaging.version.parse(lib["version"])
            if latest_version is None or ver > latest_version:
                latest_version = ver
                latest_version_lib = lib
        assert latest_version_lib is not None
        selected_libraries.append(latest_version_lib)

    libraries_count = len(selected_libraries)
    libraries_per_job = (libraries_count + args.parallel - 1) // args.parallel

    print(f"Parallel: {args.parallel}, libraries total: {len(libraries_list)}, "
          f"libraries filtered: {libraries_count}, per job: {libraries_per_job}")

    jobs_matrix = {
        "include": [
            {"index": n} for n in range(args.parallel)
        ]
    }
    print(f"::set-output name=matrix::{json.dumps(jobs_matrix)}")

    if args.parallel == 1:
        with open(args.output, 'w') as out:
            json.dump(selected_libraries, out)
    else:
        for part in range(args.parallel):
            out_name_prefix, out_ext = os.path.splitext(args.output)
            out_name = f'{out_name_prefix}{part}{out_ext}'
            libraries_part = selected_libraries[part * libraries_per_job : (part + 1) * libraries_per_job]
            with open(out_name, 'w') as out:
                json.dump(libraries_part, out)


if __name__ == "__main__":
    main()

