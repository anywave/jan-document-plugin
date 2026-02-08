; Jan Document Plugin - Bootstrap Installer
; Handles FULL installation including Python 3.12
; Version 2.0.0-beta
;
; This installer:
; 1. Checks/installs Python 3.12
; 2. Installs Tesseract OCR
; 3. Extracts application files
; 4. Installs Python dependencies
; 5. Creates shortcuts and runs

#define MyAppName "Jan Document Plugin"
#define MyAppVersion "2.0.0-beta"
#define MyAppPublisher "Anywave Creations"
#define MyAppURL "https://github.com/anywave/jan-document-plugin"
#define PythonVersion "3.12.8"
#define PythonInstaller "python-3.12.8-amd64.exe"

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
Compression=lzma2/ultra64
SolidCompression=yes

; UI settings
WizardStyle=modern
WizardSizePercent=120
SetupLogging=yes

; Privileges - need admin for Python install
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; License and info
LicenseFile=..\LICENSE
InfoBeforeFile=docs\bootstrap_info.txt

; Uninstaller
UninstallDisplayName={#MyAppName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked
Name: "installpython"; Description: "Install Python 3.12 (required)"; GroupDescription: "Dependencies:"; Flags: checkedonce
Name: "installtesseract"; Description: "Install Tesseract OCR (optional)"; GroupDescription: "Dependencies:"; Flags: checkedonce

[Files]
; Source Python files (not compiled exe)
Source: "..\*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\*.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.env.example"; DestDir: "{app}"; DestName: "config.env"; Flags: onlyifdoesntexist

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion

; Calibration
Source: "..\calibration\*"; DestDir: "{app}\calibration"; Flags: ignoreversion recursesubdirs

; Bundled LLM (if exists - ~5GB)
Source: "llm\*"; DestDir: "{app}\llm"; Flags: ignoreversion recursesubdirs; Check: DirExists(ExpandConstant('{src}\llm'))
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs; Check: DirExists(ExpandConstant('{src}\models'))

; Python installer (embedded)
Source: "downloads\{#PythonInstaller}"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: ShouldInstallPython(); Tasks: installpython

[Dirs]
Name: "{app}\jan_doc_store"; Permissions: users-modify
Name: "{app}\venv"; Permissions: users-modify
Name: "{app}\llm"; Permissions: users-modify
Name: "{app}\models"; Permissions: users-modify

[Icons]
; Start Menu
Name: "{group}\{#MyAppName}"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\start-stack.ps1"""; WorkingDir: "{app}"; Comment: "Start Jan Document Plugin"
Name: "{group}\Open Chat UI"; Filename: "http://localhost:1338/ui"
Name: "{group}\Configuration"; Filename: "{app}\config.env"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop (optional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\start-stack.ps1"""; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Start Jan Document Plugin"

[Run]
; Install Python 3.12 if needed
Filename: "{tmp}\{#PythonInstaller}"; Parameters: "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0"; StatusMsg: "Installing Python 3.12..."; Flags: waituntilterminated; Check: ShouldInstallPython(); Tasks: installpython

; Install Tesseract via winget
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""winget install UB-Mannheim.TesseractOCR --accept-source-agreements --accept-package-agreements"""; StatusMsg: "Installing Tesseract OCR..."; Flags: waituntilterminated runhidden; Tasks: installtesseract

; Create virtual environment and install dependencies
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -File ""{app}\install.ps1"""; WorkingDir: "{app}"; StatusMsg: "Installing Python dependencies..."; Flags: waituntilterminated

; Launch application
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\start-stack.ps1"""; WorkingDir: "{app}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent unchecked

[Code]
var
  PythonPath: String;

function ShouldInstallPython(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;

  // Check if Python 3.12 is already installed
  if Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := False;
    Log('Python already installed');
  end
  else if Exec('py', '-3.12 --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := False;
    Log('Python 3.12 found via py launcher');
  end;
end;

function FindPython(): String;
var
  ResultCode: Integer;
  PythonOutput: AnsiString;
  PossiblePaths: Array[0..3] of String;
  I: Integer;
begin
  Result := '';

  PossiblePaths[0] := 'python';
  PossiblePaths[1] := 'py -3.12';
  PossiblePaths[2] := ExpandConstant('{localappdata}\Programs\Python\Python312\python.exe');
  PossiblePaths[3] := 'C:\Program Files\Python312\python.exe';

  for I := 0 to 3 do
  begin
    if FileExists(PossiblePaths[I]) or (I < 2) then
    begin
      if Exec(PossiblePaths[I], '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
      begin
        Result := PossiblePaths[I];
        Log('Found Python at: ' + Result);
        Break;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    Log('Post-install: Finding Python...');
    PythonPath := FindPython();

    if PythonPath = '' then
    begin
      MsgBox('Python 3.12 was not found. Please install Python manually and run install.ps1', mbError, MB_OK);
      Exit;
    end;

    Log('Using Python: ' + PythonPath);
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;

  // Welcome message
  if MsgBox('Jan Document Plugin Setup' + #13#10#13#10 +
            'This installer will:' + #13#10 +
            '• Install Python 3.12 (if needed)' + #13#10 +
            '• Install Tesseract OCR (if selected)' + #13#10 +
            '• Install all Python dependencies' + #13#10 +
            '• Set up the Jan Document Plugin' + #13#10#13#10 +
            'Estimated time: 5-10 minutes' + #13#10 +
            'Disk space required: ~500MB (or ~8GB with bundled LLM)' + #13#10#13#10 +
            'Continue?',
            mbConfirmation, MB_YESNO) = IDNO then
  begin
    Result := False;
  end;
end;
