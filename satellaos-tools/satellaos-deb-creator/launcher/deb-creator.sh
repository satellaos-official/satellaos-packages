#!/bin/bash

name=deb-creator
tool_url=https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/core/deb-creator.py
dark_mode_url=https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/icons/theme/darkmode.png
light_mode_url=https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/icons/theme/lightmode.png
location=$HOME/.local/share

# - Creating The File Location -
mkdir -p "$location/$name"

# - Downloading The Tool -
wget -O "$location/$name/run.py" "$tool_url"
wget -O "$location/$name/darkmode.png" "$dark_mode_url"
wget -O "$location/$name/lightmode.png" "$light_mode_url"

# - Opening The Tool -
python3 "$location/$name/run.py" "$@"