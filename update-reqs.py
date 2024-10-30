#!/usr/bin/env python3
#
# Update requirements.txt to reflect versions installed using the YML file
#
import os
import re
import subprocess

REPO_DIR = os.path.dirname(__file__)

def main():
    reqs_in  = os.path.join(REPO_DIR, "requirements.in")
    reqs_out = os.path.join(REPO_DIR, "requirements.txt")

    with open(reqs_in) as f:
        pkgs = [line.strip() for line in f.readlines() if not line.startswith('#')]

    expr = '(' + '|'.join(pkgs) + ')'
    cmd = f"conda list -f '{expr}' | egrep -v '^#'"
    # | egrep -i '{expr}'

    # print(cmd)
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)

    # print(f"Lines:\n{proc.stdout}")

    lines = proc.stdout.split('\n')
    with open(reqs_out, 'w') as f:
        f.write("# This file was generated by the script update-reqs.py. Manual edits may be lost.\n")
        for line in lines:
            if not line:
                continue
            # print(f"Line is '{line}'")
            name, version, _, _ = re.split(r'\s+', line)
            f.write(f"{name}=={version}\n")

main()
