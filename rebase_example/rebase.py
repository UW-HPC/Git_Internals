#!/usr/bin/env python
"""
Naive implementation of 'git rebase', for the Git Internals workshop hosted by
the Research Computing Club at the University of Washington

Copyright (C) 2019 Andrew Wildman

Licensed by the MIT license. See LICENSE for more details
"""

import os
import sys

# Helper functions to abstract ugly details of python/os interactions
from git_workshop_helper import *


def dereference(branch):
    """
    Get the commit hashes from possible branches
    """
    # Get all branch names
    refs = call('find .git/refs/heads -type f')
    refs = set([ref.replace('.git/refs/heads/','') for ref in refs])

    # Check if the branch can be dereferenced and returned
    if branch in refs:
        return call('cat .git/refs/heads/' + branch)[0]
    else:
        return branch


def get_commit_info(commit_hash):
    """
    Return the tree hash, parents, and message of a commit
    """
    parents = set()
    tree = None
    message = ""
    cat_file = call('git cat-file -p ' + commit_hash)
    message_start = False
    for line in cat_file:

        if 'parent' in line:
            parents.add(line.split()[1])

        if 'tree' in line:
            tree = line.split()[1]

        if 'committer' in line:
            message_start = True
            continue

        if message_start:
            message += line

    return tree, parents, message


def get_parents(commit_hash):
    """
    Find the parents of the current commit
    """
    return get_commit_info(commit_hash)[1]


def set_from_history(commit_hash, history=set()):
    """
    Get a set of commit hashes in the history of a commit
    """
    parents = get_parents(commit_hash)

    # Recursively add parent's history to this commit's
    for parent in parents:
        if parent not in history:
            history.update(set_from_history(parent, history)) 

    # Add this commit to the history and return
    history.add(commit_hash)
    return history


def get_rebase_commits(rebase_commit, other_history, commit_list=[]):
    """
    Finds all the commits that need to be applied to rebase the commit.
    """

    # If this commit is in the other branch history, nothing needs to be done
    if rebase_commit in other_history:
        return []

    # Recursively add parent's to commits that need to be rebased 
    parents = get_parents(rebase_commit)
    for parent in parents:
        if parent not in commit_list:
            plist = get_rebase_commits(parent, other_history, commit_list)
            commit_list = [*commit_list, *plist]

    commit_list = [*commit_list, rebase_commit]

    return commit_list


def reapply_commits(commit_list, new_base, other_history):
    """
    Reapplies the commits on top of the new_base
    """

    commit_map = {}

    for commit in commit_list:
        tree, parents, message = get_commit_info(commit)
        new_parents = set()
        for parent in parents:
            if parent in other_history:
                new_parents.add(new_base)
            elif parent in commit_map:
                new_parents.add(commit_map[parent])


        # Write message to file temporarily
        fil = open('rebase_message.tmp', 'w')
        fil.write(message)
        fil.close()

        # Create the commit-tree call
        command = "git commit-tree {} -F rebase_message.tmp".format(tree)
        for parent in new_parents:
            command += ' -p ' + parent
        new_hash = call(command)[0]

        # Clean up and mark new commit hash
        os.remove('rebase_message.tmp')
        commit_map[commit] = new_hash

    return commit_map[commit_list[-1]]


def update_reference(branch, commit_hash):
    """
    Moves branch to point to commit_hash
    """
    call("git update-ref refs/heads/{} {}".format(branch, commit_hash))


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: ./rebase <old branch> <new base>")
        exit(1)

    # Get the commit hashes of the user's input
    branch_name = sys.argv[1]
    old_branch = dereference(branch_name)
    new_base = dereference(sys.argv[2])

    # Find the commits that need to be reapplied to rebase
    new_base_history = set_from_history(new_base) 
    rebase_commits = get_rebase_commits(old_branch, new_base_history)

    # Reapply those commits on the new base
    new_top = reapply_commits(rebase_commits, new_base, new_base_history)
    print("Top of rebased commits: " + new_top)

    # Update reference (if there was one)
    if branch_name != old_branch:
        update_reference(branch_name, new_top)
