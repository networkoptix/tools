#!/usr/bin/env python


from __future__ import print_function
import os
import sys


sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from mercurial_utils import HgContext


def auto_rebase():
    hg = HgContext()

    heads = hg.heads(".")

    if len(heads) < 2:
        print("Current branch has only one head. Nothing to rebase.")
        exit(1)

    public_heads = [head for head in heads if hg.phase(head) == "public"]
    if not public_heads:
        print("Current branch has no public heads. Don't know where to merge.")
        exit(1)
    if len(public_heads) > 1:
        print("Current branch has multiple public heads. Don't know where to merge.")
        exit(1)

    dest = public_heads[0]

    private_heads = [head for head in heads if head not in public_heads]
    if not private_heads:
        print("Current branch has no private heads.")
        exit(1)

    base = None
    if hg.phase(".") == "public":
        if len(private_heads) > 1:
            print("You have multiple private heads. Cannot rebase automatically.")
            exit(1)
        else:
            base = private_heads[0]

    print("Rebasing {} to {}".format(base if base else ".", dest))
    hg.rebase(base=base, dest=dest)

    if base:
        hg.update()


auto_rebase()
