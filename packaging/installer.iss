#define MyAppName "AOA"
#define MyAppPublisher "AOA"
#define MyAppExeName "AOA.exe"
#ifndef MyAppVersion
  #define MyAppVersion "0.11.2"
#endif

[Setup]
AppId={{5D6E5A58-BE73-4A50-93CA-4027B790D5BA}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\AOA
DefaultGroupName=AOA
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=AOA-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=..\src\AOA\assets\brand\aoa.ico
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "desktopicon"; Description: "Utworz skrot na pulpicie"; GroupDescription: "Dodatkowe skroty:"

[Files]
Source: "..\dist\AOA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\AOA"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\AOA"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Uruchom AOA"; Flags: nowait postinstall skipifsilent
