#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif

[Setup]
AppName=Polis_AI
AppVersion={#MyAppVersion}
AppPublisher=Enrico Martini
DefaultDirName={autopf}\Polis_AI
DefaultGroupName=Polis_AI
OutputDir=Output
OutputBaseFilename=Polis_AI_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin

[Files]
Source: "dist\Polis_AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Polis_AI"; Filename: "{app}\Polis_AI.exe"
Name: "{autodesktop}\Polis_AI"; Filename: "{app}\Polis_AI.exe"