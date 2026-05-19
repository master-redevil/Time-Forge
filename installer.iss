[Setup]
AppName=Time Forge
AppVersion=1.0.0
AppPublisher=msp.co
DefaultDirName={autopf}\Time Forge
DefaultGroupName=Time Forge
UninstallDisplayIcon={app}\TimeForge.exe
Compression=lzma2
SolidCompression=yes
OutputDir=dist
OutputBaseFilename=TimeForge_Setup
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=lowest
SetupIconFile=assets\logo.ico

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\TimeForge.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Time Forge"; Filename: "{app}\TimeForge.exe"
Name: "{group}\{cm:UninstallProgram,Time Forge}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Time Forge"; Filename: "{app}\TimeForge.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TimeForge.exe"; Description: "{cm:LaunchProgram,Time Forge}"; Flags: nowait postinstall skipifsilent
