; Jan Document Plugin - Inno Setup Script
; Creates a Windows installer (setup.exe)
;
; Prerequisites:
; 1. Build the exe first: build_exe.bat
; 2. Install Inno Setup: https://jrsoftware.org/isinfo.php
; 3. Compile this script with Inno Setup
;
; The installer will:
; - Install to Program Files
; - Create Start Menu shortcuts
; - Create Desktop shortcut (optional)
; - Register uninstaller

#define MyAppName "Jan Document Plugin"
#define MyAppVersion "2.0.0-beta"
#define MyAppPublisher "Anywave Creations"
#define MyAppURL "https://github.com/anywave/jan-document-plugin"
#define MyAppExeName "JanDocumentPlugin.exe"

[Setup]
; App identity
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Install locations
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Output settings
OutputDir=..\dist\installer
OutputBaseFilename=JanDocumentPlugin_Setup_{#MyAppVersion}
; Icon - uses generated icon if available, otherwise Inno Setup default
#ifexist "..\assets\icon.ico"
SetupIconFile=..\assets\icon.ico
#endif
Compression=lzma2/ultra64
SolidCompression=yes

; UI settings
WizardStyle=modern
WizardSizePercent=120

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; License and info
LicenseFile=..\LICENSE
InfoBeforeFile=..\docs\pre_install_info.txt

; Uninstaller
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Start with Windows"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
; Main application files from PyInstaller dist folder
Source: "..\dist\JanDocumentPlugin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Chat UI
Source: "..\chat_ui.html"; DestDir: "{app}"; Flags: ignoreversion

; Bundled LLM engine (llama-server + Vulkan DLLs)
Source: "llm\*"; DestDir: "{app}\llm"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\llm'))

; Bundled model (~5GB)
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: DirExists(ExpandConstant('{src}\models'))

; Config file (don't overwrite if exists)
Source: "..\config.env.example"; DestDir: "{app}"; DestName: "config.env"; Flags: onlyifdoesntexist

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Calibration files
Source: "..\calibration\JanDocPlugin_Calibration.pdf"; DestDir: "{app}\calibration"; Flags: ignoreversion

; Jan rollback helper
Source: "..\rollback_jan.ps1"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create data directories
Name: "{app}\jan_doc_store"; Permissions: users-modify
Name: "{app}\tesseract"; Permissions: users-modify
Name: "{app}\llm"; Permissions: users-modify
Name: "{app}\models"; Permissions: users-modify

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Start Jan Document Plugin"
Name: "{group}\Open Chat UI"; Filename: "http://localhost:1338/ui"; IconFilename: "{sys}\shell32.dll"; IconIndex: 13
Name: "{group}\Configuration"; Filename: "{app}\config.env"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Start Jan Document Plugin"

[Registry]
; Auto-start (optional)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "JanDocumentPlugin"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: autostart

[Run]
; Post-install actions
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "http://localhost:1338"; Description: "Open Web Interface"; Flags: shellexec postinstall skipifsilent unchecked

[Code]
const
  RequiredJanVersion = '0.6.8';

function GetJanVersion(): String;
var
  JanDir, PackageJsonPath, Content: String;
  StartPos, EndPos: Integer;
begin
  Result := '';
  JanDir := ExpandConstant('{localappdata}\Programs\jan');

  if not DirExists(JanDir) then
    Exit;

  PackageJsonPath := JanDir + '\resources\app.asar.unpacked\package.json';
  if not FileExists(PackageJsonPath) then
  begin
    PackageJsonPath := JanDir + '\resources\app\package.json';
    if not FileExists(PackageJsonPath) then
      Exit;
  end;

  if LoadStringFromFile(PackageJsonPath, Content) then
  begin
    StartPos := Pos('"version"', Content);
    if StartPos > 0 then
    begin
      StartPos := Pos(':', Copy(Content, StartPos, Length(Content))) + StartPos;
      StartPos := Pos('"', Copy(Content, StartPos, Length(Content))) + StartPos;
      EndPos := Pos('"', Copy(Content, StartPos, Length(Content))) + StartPos - 1;
      if (StartPos > 0) and (EndPos > StartPos) then
        Result := Copy(Content, StartPos, EndPos - StartPos);
    end;
  end;
end;

function InitializeSetup(): Boolean;
var
  JanVersion, Msg: String;
begin
  Result := True;
  JanVersion := GetJanVersion();

  if JanVersion = '' then
  begin
    if MsgBox('Jan AI was not detected on this system.' + #13#10 + #13#10 +
              'The plugin bundles its own LLM server (llama-server) so it can run independently.' + #13#10 +
              'However, Jan v' + RequiredJanVersion + ' is recommended for the best experience.' + #13#10 + #13#10 +
              'Continue installation?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end
  else if Pos(RequiredJanVersion, JanVersion) <> 1 then
  begin
    Msg := 'Jan v' + JanVersion + ' detected, but this plugin is designed for Jan v' + RequiredJanVersion + '.' + #13#10 + #13#10 +
           'Newer versions of Jan may have breaking API changes.' + #13#10 +
           'You can download Jan v' + RequiredJanVersion + ' from:' + #13#10 +
           'https://github.com/janhq/jan/releases/tag/v' + RequiredJanVersion + #13#10 + #13#10 +
           'A rollback helper script (rollback_jan.ps1) will be included.' + #13#10 + #13#10 +
           'Continue installation anyway?';
    if MsgBox(Msg, mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-install tasks if needed
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nJan Document Plugin v2.0.0-beta is a self-contained package including:%n- Qwen 2.5 7B model (q4_k_m quantization)%n- llama-server with Vulkan GPU support%n- Document RAG with offline embeddings%n- Voice input, drill-down, and research tools%n- Consciousness pipeline%n%nRequires ~8 GB disk space.%n%nRecommended: Jan AI v0.6.8 (optional - plugin can run standalone)
FinishedLabel=Setup has finished installing [name] on your computer.%n%nBundled components:%n- llama-server (Vulkan GPU)%n- Qwen 2.5 7B Instruct (q4_k_m)%n- Chat UI with voice input and discovery%n%nTo use:%n1. Launch Jan Document Plugin from the Start Menu%n2. The Chat UI opens automatically in your browser%n3. Upload documents and chat - everything runs locally!
