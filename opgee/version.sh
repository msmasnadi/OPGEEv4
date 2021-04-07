#!/bin/bash

topdir="$(git rev-parse --show-toplevel)"
filename="$topdir/opgee/version.py"

version=`git diff HEAD^..HEAD -- "$filename" | perl -ne 'print $1 if /^\+VERSION="(.+)"$/'`
echo $version

