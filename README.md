# SatellaOS Packages

A collection of tools developed for the **SatellaOS GNU/Linux** ecosystem.

SatellaOS is based on **Debian 13 XFCE**, and most tools in this repository can also be used on standard Debian-based systems.

---

## Repository Structure

Each tool is organized using the following directory structure:

### `core`

Contains the main source code of the application. All functionality depends on the files located in this directory.

### `launcher`

Contains a launcher script that automatically downloads the latest version of the tool from the internet and executes it from the `/tmp` directory.

### `package`

Contains the packaged `.deb` version of the tool. Required dependencies are installed automatically through the package.

### `dependencies`

Includes a Bash script that installs all dependencies required by the tool.

### `icons`

Contains application icons and related graphical assets.

---

# Available Tools

## SatellaOS Deb Creator

Create Debian packages quickly and easily using either a graphical interface or the terminal.

### Downloads

**Core**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/core/deb-creator.py
```

**Launcher**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/launcher/deb-creator.sh
```

**Package**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-deb-creator/package/satellaos-deb-creator_1.0.0_amd64.deb
```

---

## SatellaOS Papirus Color Manager

Change the colors of the Papirus icon theme with a single click.

### Downloads

**Core**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-papirus-color-manager/core/papirus-color-manager.py
```

**Launcher**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-papirus-color-manager/launcher/papirus-color-manager.sh
```

**Package**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-papirus-color-manager/package/satellaos-papirus-color-manager_1.0.0_amd64.deb
```

---

## SatellaOS UCA Creator

Generate an XFCE `uca.xml` file with predefined custom actions.

### Features

* Includes 14 built-in right-click actions.
* Allows selective installation of available actions.
* Designed for XFCE users.

### Warning

> If you already have a customized `uca.xml` file, some or all existing entries may be overwritten. Creating a backup before use is strongly recommended.

### Downloads

**Core**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-uca-creator/core/uca-creator.py
```

**Launcher**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-uca-creator/launcher/uca-creator.sh
```

**Package**

```
https://raw.githubusercontent.com/satellaos-official/satellaos-packages/refs/heads/main/satellaos-tools/satellaos-uca-creator/package/satellaos-uca-creator_1.0.0_amd64.deb
```

---

## License

Unless otherwise specified, the tools contained in this repository are distributed under the license provided by their respective projects.
