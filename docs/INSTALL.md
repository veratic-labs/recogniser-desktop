# Installing recogniser

This document is for someone installing a finished build. To build it from
source, see [BUILDING.md](BUILDING.md).

## Requirements

| Requirement | Notes |
| --- | --- |
| Windows 10 or 11, x64 | Windows on ARM is not supported |
| Microsoft Edge WebView2 Runtime | Preinstalled on most Windows 11 computers and installed with Microsoft Edge. The application reports its absence when it starts |
| Microsoft Visual C++ 2015–2022 Redistributable (x64) | Present on most machines; needed by the bundled native libraries |

Python is **not** required. The installer contains a complete private runtime.

## Verify the download

Each installer is distributed with a `.sha256` file next to it. To compare, in
PowerShell:

```powershell
Get-FileHash .\recogniser-1.0.0-setup.exe -Algorithm SHA256
```

The printed hash must equal the contents of
`recogniser-1.0.0-setup.exe.sha256`.

The installer is not code signed, so Windows SmartScreen may show "Windows
protected your PC" the first time it runs. Use **More info** → **Run anyway** only
after the hash matches.

## Install

1. Run `recogniser-<version>-setup.exe`.
2. Accept the default location or choose another.
3. The desktop shortcut is an optional, unchecked task; a Start-menu shortcut is
   always created.
4. Finish the wizard. The last page offers **Launch recogniser**.

The installer requests no administrator rights: it installs for the current user
under `%LOCALAPPDATA%\Programs\recogniser`. `packaging\recogniser.iss` sets
`PrivilegesRequired=lowest`, so an installation for all users is not offered.

Unattended install:

```powershell
.\recogniser-1.0.0-setup.exe /SILENT /SUPPRESSMSGBOXES /NORESTART
```

## Launch

Use the Start-menu shortcut **recogniser**, the optional desktop shortcut, or:

```powershell
& "$env:LOCALAPPDATA\Programs\recogniser\recogniser.exe"
```

The window opens on the category list. Choose a category, upload an image or draw
a digit, then choose **Recognise**.

## Where your data lives

The application never writes inside its install directory. It keeps its own data
in:

```text
%LOCALAPPDATA%\recogniser\
  logs\recogniser.log     application log, including recognition errors
  logs\self-test.json     written only when --self-test runs
  webview-data\           embedded-browser storage, created on first launch
```

To relocate that directory, set `RECOGNISER_DATA_DIR` to an **absolute** path
before launching. A relative value is rejected so that data cannot be scattered
across arbitrary directories:

```powershell
$env:RECOGNISER_DATA_DIR = 'D:\recogniser-data'
& "$env:LOCALAPPDATA\Programs\recogniser\recogniser.exe"
```

Nothing is written to the registry apart from the standard uninstall entry that
lets Windows list and remove the application.

## Upgrade

Run the newer `recogniser-<version>-setup.exe`. It uses the same `AppId`, so
Windows treats it as the same product: the files in the install directory are
replaced and your data under `%LOCALAPPDATA%\recogniser` is untouched. There is no
downgrade protection, so an older installer can also be run over a newer
installation.

## Uninstall

Use **Settings → Apps → Installed apps → recogniser → Uninstall**, or
**Control Panel → Programs and Features**. The uninstaller removes the install
directory, the Start-menu shortcut, and the optional desktop shortcut.

It does **not** remove `%LOCALAPPDATA%\recogniser`, because that directory
contains your logs and is outside the install directory, and the script has no
`[UninstallDelete]` entry. Delete it manually only if you also want the logs and
browser storage gone:

```powershell
Remove-Item -LiteralPath "$env:LOCALAPPDATA\recogniser" -Recurse -Force
```

A `RECOGNISER_DATA_DIR` directory is never touched by the uninstaller.

Unattended uninstall:

```powershell
& "$env:LOCALAPPDATA\Programs\recogniser\unins000.exe" /SILENT
```

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| "recogniser cannot start" and a message about the WebView2 Runtime | Install the Microsoft Edge WebView2 Runtime, then start the application again |
| The window does not open and nothing appears | Read `%LOCALAPPDATA%\recogniser\logs\recogniser.log`; startup failures are logged there |
| "Something went wrong while loading the model" | The installation is incomplete or the model files are missing. Reinstall; the log has the underlying error |
| SmartScreen blocks the installer | The installer is unsigned. Check the SHA-256 first, then choose **More info** → **Run anyway** |
| Setup refuses to continue on Windows on ARM | Only x64 is built and tested |
| An old version still starts after installing a newer one | The Start-menu shortcut may point at a different copy. Uninstall the old version first |

If the application misbehaves after an upgrade, run the bundled self-test from a
PowerShell window to see which step fails:

```powershell
$env:RECOGNISER_DATA_DIR = "$env:TEMP\recogniser-selftest"
$process = Start-Process -FilePath "$env:LOCALAPPDATA\Programs\recogniser\recogniser.exe" `
    -ArgumentList '--self-test' -WindowStyle Hidden -Wait -PassThru
$process.ExitCode
Get-Content "$env:RECOGNISER_DATA_DIR\logs\self-test.json"
```

## Not included

- Code signing, so SmartScreen reputation has to build up on its own.
- Automatic updates; install a newer setup file to upgrade.
- A portable (no-install) build. The bundle in `dist\recogniser` runs in place,
  but it is distributed only through the installer.

