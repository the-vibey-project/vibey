#!/bin/sh
# Copies the live, append-only results (written while experiments run, so never tracked:
# a pre-push hook that sees them change mid-run refuses the push) into data/, which is.
cd "$(dirname "$0")/.." || exit 1
rsync -a --delete --exclude '.model.lock' --exclude 'scratch/' results/ data/
