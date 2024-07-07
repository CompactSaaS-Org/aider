#!/usr/bin/env python3

import subprocess
import sys
import tempfile
import argparse
from collections import defaultdict
from pathlib import Path
from aider.dump import dump
import os


def get_all_commit_hashes_since_tag(tag):
    res = run(["git", "rev-list", f"{tag}..HEAD"])

    if res:
        commit_hashes = res.strip().split('\n')
        return commit_hashes

def run(cmd):
    try:
        # Get all commit hashes since the specified tag
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error: {e}", file=sys.stderr)
        return

def get_commit_authors(commits):
    commit_to_author = dict()
    for commit in commits:
        author = run(["git", "show", "-s", "--format=%an", commit]).strip()
        commit_to_author[commit] = author
    return commit_to_author


hash_len = len('44e6fefc2')

def main():
    parser = argparse.ArgumentParser(description="Get commit hashes since a specified tag.")
    parser.add_argument("tag", help="The tag to start from")
    args = parser.parse_args()

    commits = get_all_commit_hashes_since_tag(args.tag)
    commits = [commit[:hash_len] for commit in commits]

    authors = get_commit_authors(commits)

    py_files = run(['git', 'ls-files', '*.py']).strip().split('\n')

    all_file_counts = {}
    for file in py_files:
        file_counts = get_counts_for_file(args.tag, authors, file)
        if file_counts:
            all_file_counts[file] = file_counts

    dump(all_file_counts)

def get_counts_for_file(tag, authors, fname):
    text = run(['git', 'blame', f'{tag}..HEAD', '--', fname])
    if not text:
        return None
    text = text.splitlines()
    line_counts = defaultdict(int)
    for line in text:
        if line.startswith('^'):
            continue
        hsh = line[:hash_len]
        author = authors.get(hsh, "Unknown")
        line_counts[author] += 1

    return dict(line_counts)

if __name__ == "__main__":
    main()
