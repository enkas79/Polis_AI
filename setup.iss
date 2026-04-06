#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif

[Setup]
AppName=Polis_AI
AppVersion={#MyAppVersion}
AppPublisher=Enrico Martini
DefaultDirName={localappdata}\Programs\Polis_AI
DefaultGroupName=Polis_AI
OutputDir=Output
OutputBaseFilename=Polis_AI_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest
SetupIconFile=assets\icon.ico

[Files]
Source: "dist\Polis_AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; --- COPIA ESPLICITA DEI FILE VITALI ---
Source: "scenarios\*"; DestDir: "{app}\scenarios"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "version.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; --- AGGIUNTO WORKINGDIR PER EVITARE CHE WINDOWS SI CONFONDA ---
Name: "{group}\Polis_AI"; Filename: "{app}\Polis_AI.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Polis_AI"; Filename: "{app}\Polis_AI.exe"; WorkingDir: "{app}"
