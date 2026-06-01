# 📦 SatellaOS Packages

This repository contains tools developed for the **SatellaOS GNU/Linux** ecosystem.

SatellaOS is based on **Debian 13 XFCE**, and most tools provided here can also be used on standard Debian-based systems.

---

# 📁 Repository Structure

Each tool is organized using the following directory layout:

| Directory        | Description                                                                                                                              |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| **core**         | Contains the main source files required for the application to function. Everything depends on this directory.                           |
| **launcher**     | Contains a lightweight launcher script. Each time it runs, it downloads the latest version of the main script to `/tmp` and executes it. |
| **package**      | Contains the packaged `.deb` version of the tool. Required dependencies are automatically installed during package installation.         |
| **dependencies** | Contains a Bash script that installs all dependencies required by the tool.                                                              |
| **icons**        | Contains application icons and related graphical assets.                                                                                 |

---

# 🛠️ SatellaOS Deb Creator

A utility that allows users to create Debian packages effortlessly through either a graphical interface or the terminal.

## Downloads

### Core

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/core/deb-creator.py

### Launcher

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/launcher/deb-creator.sh

### Package

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/package/satellaos-deb-creator_1.0.0_amd64.deb

---

# 🎨 SatellaOS Papirus Color Manager

A tool that allows users to change the colors of the Papirus icon theme with a single click.

## Downloads

### Core

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-papirus-color-manager/core/papirus-color-manager.py

### Launcher

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-papirus-color-manager/launcher/papirus-color-manager.sh

### Package

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-papirus-color-manager/package/satellaos-papirus-color-manager_1.0.0_amd64.deb

---

# 🖱️ SatellaOS UCA Creator

Creates an `uca.xml` configuration file for XFCE custom actions.

The generated file contains **14 predefined context menu actions**, and users can choose which actions should be added to the right-click menu.

> **Warning**
>
> If you already have a customized `uca.xml` file, its contents may be overwritten. Creating a backup before use is strongly recommended.

## Downloads

### Core

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-uca-creator/core/uca-creator.py

### Launcher

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-uca-creator/launcher/uca-creator.sh

### Package

https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-uca-creator/package/satellaos-uca-creator_1.0.0_amd64.deb

---

---

# 📜 License

This project is licensed under the **MIT License**.

You are free to use, modify, distribute, and redistribute the software, provided that the original copyright notice and license text are included.

For more information, see the `LICENSE` file included in this repository.
