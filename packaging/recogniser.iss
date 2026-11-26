; Inno Setup 7 script for the recogniser Windows desktop application.
;
; Compile only through packaging\build.ps1 -Installer. That script verifies that
; dist\recogniser still matches the reviewed build\bundle-manifest.json before
; and after compiling, and it supplies the version from packaging\version.txt:
;
;   ISCC.exe /DAppVersion=1.0.0 /DAppVersion4=1.0.0.0 packaging\recogniser.iss
;
; This script never builds the application: it packages the bundle exactly as it
; was built and reviewed in the previous stage. There is no [UninstallDelete]
; entry, so user data outside the install directory is never removed.

#ifndef AppVersion
  #error AppVersion must be supplied by packaging\build.ps1
#endif

#ifndef AppVersion4
  #error AppVersion4 must be supplied by packaging\build.ps1
#endif

[Setup]
; Stable product identity. Never change this value: a new AppId makes Windows
; treat the release as a different product and leave the old version installed.
AppId={{76658801-C6D0-4BEF-BCF2-2093DB21D42E}
AppName=recogniser
AppVersion={#AppVersion}
AppVerName=recogniser {#AppVersion}
; Per-user install: no elevation, and {autopf} resolves to the user's
; %LOCALAPPDATA%\Programs directory instead of Program Files.
DefaultDirName={autopf}\recogniser
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
DisableWelcomePage=no
WizardStyle=modern
OutputDir=..\dist\installer
OutputBaseFilename=recogniser-{#AppVersion}-setup
SetupIconFile=assets\recogniser.ico
UninstallDisplayName=recogniser {#AppVersion}
UninstallDisplayIcon={app}\recogniser.exe
Compression=lzma2/max
SolidCompression=yes
; x64 only. ArchitecturesAllowed=x64compatible alone would also accept Windows
; on ARM, where no build of this application has been tested.
SetupArchitecture=x64
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion={#AppVersion4}
VersionInfoProductVersion={#AppVersion4}
VersionInfoTextVersion={#AppVersion}
VersionInfoProductName=recogniser
VersionInfoDescription=recogniser Setup

[Messages]
; Prerequisites are reported by the application's own startup check, so the
; installer documents them here rather than running a second, possibly
; contradictory, detection pass.
WelcomeLabel2=This will install [name/ver] on your computer.%n%nrecogniser needs the Microsoft Edge WebView2 Runtime and the Microsoft Visual C++ 2015-2022 Redistributable (x64). Both are already present on most Windows 11 computers, and the application reports a missing WebView2 Runtime when it starts.%n%nThe application keeps its own data in your local application data folder; the uninstaller does not remove that data.

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\recogniser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\recogniser"; Filename: "{app}\recogniser.exe"; IconFilename: "{app}\recogniser.exe"
Name: "{autodesktop}\recogniser"; Filename: "{app}\recogniser.exe"; IconFilename: "{app}\recogniser.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\recogniser.exe"; Description: "Launch recogniser"; Flags: nowait postinstall skipifsilent
