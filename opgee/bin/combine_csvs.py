#!/usr/bin/env python
#
# Combine CSV files of the same structure (number and names of columns) into a single CSV.
#
# Rich Plevin
# 28-OCT-2021
#
import argparse
import pandas as pd

DEFAULT_OUTPUT = 'combined.csv'

def parseArgs():
    parser = argparse.ArgumentParser(description='''Combine CSV data into a single CSV file''')

    choices = ('rows', 'columns')
    parser.add_argument('-a', '--axis', choices=choices, default='rows',
                        help='''The axis on which to join the CSVs. Default is "rows", which requires
                        that all CSVs share the same columns. If choosing "columns", all CSVs much share
                        the same index.''')

    parser.add_argument('-o', '--output', default=DEFAULT_OUTPUT, required=True,
                        help='''The output file to create. Default is "%s".''' % DEFAULT_OUTPUT)

    parser.add_argument('inputs', nargs='*',
                        help='''Input CSV files. Must have the same number and names of columns''')

    parser.add_argument('-s', '--skip', type=int, default=0,
                        help='''A number of lines to skip before reading the column headers.''')

    args = parser.parse_args()
    return args

import glob

def main():
    args = parseArgs()

    print(f"In: {args.inputs}")
    print(f"Out: {args.output}")

    index_col = False if args.axis == 'rows' else 0
    write_index = False if args.axis == 'rows' else True

    # Expand file paths using wildcard character
    expanded_file_paths = []
    for input_file in args.inputs:
        expanded_file_paths.extend(glob.glob(input_file))

    # Read each file using the expanded file paths
    dfs = [pd.read_csv(input, index_col=index_col, skiprows=args.skip) for input in expanded_file_paths]

    combined = pd.concat(dfs, axis=args.axis)
    combined.to_csv(args.output, index=write_index)

main()

