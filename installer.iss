; Inno Setup Script for RedmineFileOrganizer
; Requires Inno Setup 6.0 or later

#define MyAppName "Redmine File Organizer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FileMove"
#define MyAppExeName "RedmineFileOrganizer.exe"

[Setup]
; アプリケーション情報
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; 出力設定
OutputDir=installer_output
OutputBaseFilename=RedmineFileOrganizer_Setup_{#MyAppVersion}
; 圧縮設定
Compression=lzma2
SolidCompression=yes
; Windows設定
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; UI設定
WizardStyle=modern
; アンインストール設定
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Windows起動時に自動起動"; GroupDescription: "自動起動設定:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; スタートメニュー
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{#MyAppName} (ウィンドウ表示)"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--show"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; デスクトップ
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
; スタートアップ
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
// アンインストール時にログファイルを削除するか確認
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  LogFile: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    LogFile := ExpandConstant('{userprofile}\RedmineFileOrganizer_log.txt');
    if FileExists(LogFile) then
    begin
      if MsgBox('ログファイルも削除しますか？' + #13#10 + LogFile, mbConfirmation, MB_YESNO) = IDYES then
      begin
        DeleteFile(LogFile);
      end;
    end;
  end;
end;
