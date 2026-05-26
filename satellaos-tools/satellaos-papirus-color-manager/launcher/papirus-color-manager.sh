#!/bin/bash

Name="papirus-color-manager"
URL="https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-$Name/core/$Name.py"
File="/tmp/$Name.py"
Location="/tmp/"

if ! wget -q --spider --timeout=5 https://raw.githubusercontent.com 2>/dev/null; then
    if command -v satellaos-netcheck &> /dev/null; then
        satellaos-netcheck
    else
        echo "Error: Internet not Found"
    fi
    exit 1
fi

rm -rf "$File"

wget -q -O "$File" "$URL"

python3 "$File" "$@"