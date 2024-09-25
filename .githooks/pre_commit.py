import difflib
import os
from pathlib import Path
import subprocess
import sys
from textwrap import dedent


def run_conda_env():
    try:
        result = subprocess.run(["conda", "env", "export"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running `conda env export`: {e}")
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
            fromfile='stored_env_out',
            tofile='current_env_out',
            n=3
        )
        return "".join(diff)
    return None

def check_output(output_file: Path = Path('py3-opgee-gh-actions.yml')):
    git_root = subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
    
    os.chdir(git_root)
    
    current_env_out = run_conda_env()
    if current_env_out is None:
        return False, "`conda env export` failed to run."

    stored_env_out = read_env_file(output_file) 
    if stored_env_out is None:
        return False, f"Failed to read from file: {output_file}"
    
    diff = compare_env_contents(current_env_out, stored_env_out)
    
    if diff:
        message = """\
Error: your environment doesn't match that defined in `py3-opgee-gh-actions.yml`.

{0}

Please remove the package or run `conda env export > py3-opgee-gh-actions.yml`, add the file, and recommit.
        """.format(diff)
        return False, dedent(message)
    else:
        return True, ""