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
#define MyAppVersion "1.2.0"
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

; Config file (don't overwrite if exists)
Source: "..\config.env.example"; DestDir: "{app}"; DestName: "config.env"; Flags: onlyifdoesntexist

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

; Calibration files
Source: "..\calibration\JanDocPlugin_Calibration.pdf"; DestDir: "{app}\calibration"; Flags: ignoreversion

[Dirs]
; Create data directories
Name: "{app}\jan_doc_store"; Permissions: users-modify
Name: "{app}\tesseract"; Permissions: users-modify

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Comment: "Start Jan Document Plugin"
Name: "{group}\Open Web Interface"; Filename: "http://localhost:1338"; IconFilename: "{sys}\shell32.dll"; IconIndex: 13
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
// Check if Jan is installed (optional warning)
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Could add check for Jan AI installation here
end;

// Show post-install instructions
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Post-install tasks if needed
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nJan Document Plugin adds document understanding to Jan AI, allowing your local LLM to read and search your documents - all offline.%n%nPrerequisites:%n- Jan AI (https://jan.ai)%n- Optional: Tesseract OCR for scanned documents
FinishedLabel=Setup has finished installing [name] on your computer.%n%nTo use:%n1. Start Jan AI and enable Local API Server%n2. Launch Jan Document Plugin%n3. Upload documents via the web interface%n4. Chat with your documents in Jan!
