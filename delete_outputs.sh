#!/usr/bin/env bash
#
# delete_outputs.sh  – remove every “outputs/” (or “output/”) directory
#                      that lives anywhere under the   data/   subtree.
#
# USAGE
#   # From the project root (or even / in WSL)
#   bash /path/to/delete_outputs.sh
#
# OPTIONS
#   -n, --dry-run   Show what would be deleted without actually deleting it.
#
# NOTES
#   • The script assumes “data/” lives beneath the current working directory,
#     so if you keep your data somewhere else, pass that path as $DATA_DIR
#     (see ENVIRONMENT VARIABLES below).
#
# ENVIRONMENT VARIABLES
#   DATA_DIR   Root of the subtree to search (default: "data").
#

set -euo pipefail

################################################################################
# 0.  Configuration
################################################################################
DATA_DIR=${DATA_DIR:-data}        # can be overridden:  DATA_DIR=/mnt/drive bash script.sh
DRY_RUN=false

################################################################################
# 1.  Parse optional flags
################################################################################
if [[ ${1:-} == "-n" || ${1:-} == "--dry-run" ]]; then
  DRY_RUN=true
  shift
fi

################################################################################
# 2.  Sanity checks
################################################################################
if [[ ! -d "$DATA_DIR" ]]; then
  echo "ERROR: '$DATA_DIR' does not exist (cwd = $(pwd))"
  echo "       Set DATA_DIR or cd to the right root first."
  exit 1
fi

################################################################################
# 3.  Locate target directories
################################################################################
mapfile -t TARGETS < <(
  find "$DATA_DIR" -type d \( -name 'outputs' -o -name 'output' \)
)

if [[ ${#TARGETS[@]} -eq 0 ]]; then
  echo "No output(s) directories found under '$DATA_DIR'."
  exit 0
fi

################################################################################
# 4.  Delete (or preview) them
################################################################################
if $DRY_RUN; then
  echo "Dry-run mode – the following directories would be removed:"
  printf '  %s\n' "${TARGETS[@]}"
else
  printf '%s\0' "${TARGETS[@]}" | xargs -0 rm -rf --
  echo "Removed ${#TARGETS[@]} folder(s) inside '$DATA_DIR'."
fi
