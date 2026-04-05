#ifndef MyAppVersion
#define MyAppVersion "0.0.0"
#endif

[Setup]
AppName=Polis_AI
AppVersion={#MyAppVersion}
AppPublisher=Enrico Martini
; 1. CAMBIATO: Installa in AppData (come Chrome/Discord) dove l'utente ha permessi totali
DefaultDirName={localappdata}\Programs\Polis_AI
DefaultGroupName=Polis_AI
OutputDir=Output
OutputBaseFilename=Polis_AI_Setup_v{#MyAppVersion}
Compression=lzma
SolidCompression=yes
; 2. CAMBIATO: Non chiede i diritti di amministratore per l'installazione
PrivilegesRequired=lowest

[Files]
Source: "dist\Polis_AI\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Polis_AI"; Filename: "{app}\Polis_AI.exe"
Name: "{autodesktop}\Polis_AI"; Filename: "{app}\Polis_AI.exe"