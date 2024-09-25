import difflib
import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent

cmd = ["conda", "list", "--export"]
cmd_str = " ".join(cmd)
list_file = "opgee-linux64.pkg_list.txt"

def run_conda_env():
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running `{cmd_str}`: {e}")
        return None
        
def read_env_file(file_path: Path):
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: File not found: {file_path}")
        return None
    
def compare_env_contents(current_env_out: str, stored_env_out: str):
    if current_env_out != stored_env_out:
        diff = difflib.unified_diff(
            stored_env_out.splitlines(keepends=True),
            current_env_out.splitlines(keepends=True),
            fromfile='environment pkg_list',
            tofile=list_file,
            n=3
        )
        return "".join(diff)
    return None

def check_output(output_file: Path = Path(list_file)):
    git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
    
    os.chdir(git_root)
    
    current_env_out = run_conda_env()
    if current_env_out is None:
        return False, f"`{cmd_str}` failed to run."

    stored_env_out = read_env_file(output_file) 
    if stored_env_out is None:
        return False, f"Failed to read from file: {output_file}"
    
    diff = compare_env_contents(current_env_out, stored_env_out)
    
    if diff:
        message = """\
Error: your environment doesn't match that defined in `{0}`.

{1}

Please remove the package(s) and/or run `{2} > {0}`, add the file, and recommit.
        """.format(list_file, diff, cmd_str)
        return False, dedent(message)
    else:
        return True, ""