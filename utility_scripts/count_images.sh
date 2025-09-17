#!/bin/bash

# Directory to search (default: current directory)
DIR="${1:-.}"

# Find all image files (case-insensitive) and count them
count=$(find "$DIR" -type f \( \
    -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \
    -o -iname "*.gif" -o -iname "*.bmp" -o -iname "*.tiff" \
    -o -iname "*.webp" -o -iname "*.heic" -o -iname "*.svg" \
\) | wc -l)

echo "Total images found in '$DIR': $count"
