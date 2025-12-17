; Inno Setup Script for RedmineFileOrganizer
; Requires Inno Setup 6.0 or later

#define MyAppName "Redmine File Organizer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FileMove"
#define MyAppExeName "RedmineFileOrganizer.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=RedmineFileOrganizer_Setup_{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "Startup Options:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} (Show Window)"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--show"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  LogFile: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    LogFile := ExpandConstant('{userprofile}\RedmineFileOrganizer_log.txt');
    if FileExists(LogFile) then
    begin
      if MsgBox('Delete log file?' + #13#10 + LogFile, mbConfirmation, MB_YESNO) = IDYES then
      begin
        DeleteFile(LogFile);
      end;
    end;
  end;
end;
