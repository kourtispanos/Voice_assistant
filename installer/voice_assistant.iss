; Build:  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer\voice_assistant.iss
; Needs dist\VoiceAssistant.exe built with:  BUNDLE_MODELS=0 pyinstaller voice_assistant.spec
; The models are downloaded during setup (they are too large for a GitHub
; release asset, which is limited to 2 GiB).

#define AppName "Voice Assistant"
#define AppVersion "1.0.0"
#define AppExe "VoiceAssistant.exe"

[Setup]
AppId={{C2A82093-AD5C-43CE-9D46-B404B3E36153}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=kourtispanos
AppPublisherURL=https://github.com/kourtispanos/Voice_assistant
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=Output
OutputBaseFilename=VoiceAssistant-Setup-{#AppVersion}
SetupIconFile=..\Voice.ico
UninstallDisplayIcon={app}\{#AppExe}
InfoBeforeFile=before-install.txt
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; The Vosk model is a .zip; the default extraction method only handles .7z.
ArchiveExtraction=full
; Models are unpacked next to the app; setup also needs room for the downloads.
ExtraDiskSpaceRequired=5000000000

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "startup"; Description: "Start the assistant when Windows starts"; GroupDescription: "Options:"; Flags: unchecked
Name: "tesseract"; Description: "Download and install Tesseract OCR (27 MB, asks for administrator permission)"; GroupDescription: "Optional components:"; Check: NeedTesseract

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\Voice.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\Voice.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\Voice.ico"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VoiceAssistant"; ValueData: """{app}\{#AppExe}"""; Tasks: startup; Flags: uninsdeletevalue

[UninstallDelete]
Type: filesandordirs; Name: "{app}\vosk-model-en-us-0.22"
Type: filesandordirs; Name: "{app}\piper_voices"
Type: filesandordirs; Name: "{app}\whisper-small"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Start {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  NL = #13#10;
  VoskUrl = 'https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip';
  VoskProbe = 'vosk-model-en-us-0.22\am\final.mdl';
  HfPiper = 'https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/jenny_dioco/medium/';
  HfWhisper = 'https://huggingface.co/Systran/faster-whisper-small/resolve/main/';
  TesseractUrl = 'https://github.com/tesseract-ocr/tesseract/releases/download/5.5.3/tesseract-ocr-w64-setup-5.5.3.20260724.exe';
  TesseractSha = 'bee9e3434bd94fd65387d9be28cd467a41f61b1275383b55b0f59a1331270ae4';
  TesseractExe = 'C:\Program Files\Tesseract-OCR\tesseract.exe';

var
  CurrentItem: String;

function NeedTesseract: Boolean;
begin
  Result := not FileExists(TesseractExe);
end;

function OnDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax > 0 then
  begin
    WizardForm.StatusLabel.Caption := Format('Downloading %s ... %d%% (%d of %d MB)', [CurrentItem, Progress * 100 div ProgressMax, Progress div 1048576, ProgressMax div 1048576]);
    WizardForm.ProgressGauge.Position :=
      WizardForm.ProgressGauge.Min + Integer((WizardForm.ProgressGauge.Max - WizardForm.ProgressGauge.Min) * Progress div ProgressMax);
  end
  else
    WizardForm.StatusLabel.Caption := Format('Downloading %s ...', [CurrentItem]);
  Result := True;
end;

// Downloads into the temp folder, retrying on failure. Returns False if the user gives up.
function Fetch(const Item, Url, FileName, Sha256: String): Boolean;
var
  Done: Boolean;
begin
  Result := False;
  CurrentItem := Item;
  Done := False;
  while not Done do
  begin
    try
      DownloadTemporaryFile(Url, FileName, Sha256, @OnDownloadProgress);
      Result := True;
      Done := True;
    except
      if SuppressibleMsgBox('Could not download ' + Item + ':' + NL + GetExceptionMessage + NL + NL +
           'Check your internet connection and try again.',
           mbError, MB_RETRYCANCEL, IDCANCEL) <> IDRETRY then
        Done := True;
    end;
  end;
end;

function OnExtractionProgress(const ArchiveName, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax > 0 then
    WizardForm.StatusLabel.Caption := Format('Unpacking the Vosk model ... %d%%', [Progress * 100 div ProgressMax]);
  Result := True;
end;

procedure PlaceFile(const TmpName, DestDir, DestName: String);
begin
  ForceDirectories(DestDir);
  if not CopyFile(ExpandConstant('{tmp}\') + TmpName, DestDir + '\' + DestName, False) then
    RaiseException('Could not copy ' + DestName + ' into ' + DestDir);
  DeleteFile(ExpandConstant('{tmp}\') + TmpName);
end;

procedure InstallVosk;
var
  Zip: String;
begin
  if FileExists(ExpandConstant('{app}\') + VoskProbe) then Exit;
  if not Fetch('the Vosk wake-word model (1.9 GB)', VoskUrl, 'vosk.zip', '') then
    RaiseException('The Vosk model is required for the wake word. Setup was cancelled.');
  Zip := ExpandConstant('{tmp}\vosk.zip');
  WizardForm.StatusLabel.Caption := 'Unpacking the Vosk model (this takes a few minutes) ...';
  try
    ExtractArchive(Zip, ExpandConstant('{app}'), '', True, @OnExtractionProgress);
  except
    RaiseException('Could not unpack the Vosk model: ' + GetExceptionMessage);
  end;
  DeleteFile(Zip);
  if not FileExists(ExpandConstant('{app}\') + VoskProbe) then
    RaiseException('The Vosk model looks incomplete after unpacking.');
end;

procedure InstallPiper;
var
  Dir: String;
begin
  Dir := ExpandConstant('{app}\piper_voices');
  if FileExists(Dir + '\en_GB-jenny_dioco-medium.onnx') and FileExists(Dir + '\en_GB-jenny_dioco-medium.onnx.json') then Exit;
  if not Fetch('the Piper voice (63 MB)', HfPiper + 'en_GB-jenny_dioco-medium.onnx', 'piper.onnx',
       '469c630d209e139dd392a66bf4abde4ab86390a0269c1e47b4e5d7ce81526b01') then
    RaiseException('The Piper voice is required. Setup was cancelled.');
  if not Fetch('the Piper voice settings', HfPiper + 'en_GB-jenny_dioco-medium.onnx.json', 'piper.json',
       'a9a7a93a317c9a3cb6563e37eb057df9ef09c06188a8a4341b0fcb58cba54dd4') then
    RaiseException('The Piper voice is required. Setup was cancelled.');
  PlaceFile('piper.onnx', Dir, 'en_GB-jenny_dioco-medium.onnx');
  PlaceFile('piper.json', Dir, 'en_GB-jenny_dioco-medium.onnx.json');
end;

procedure InstallWhisper;
var
  Dir: String;
begin
  Dir := ExpandConstant('{app}\whisper-small');
  if FileExists(Dir + '\model.bin') and FileExists(Dir + '\config.json') and
     FileExists(Dir + '\tokenizer.json') and FileExists(Dir + '\vocabulary.txt') then Exit;
  if not Fetch('the Whisper speech model (484 MB)', HfWhisper + 'model.bin', 'w_model.bin',
       '3e305921506d8872816023e4c273e75d2419fb89b24da97b4fe7bce14170d671') then
    RaiseException('The Whisper model is required. Setup was cancelled.');
  if not Fetch('the Whisper settings', HfWhisper + 'config.json', 'w_config.json',
       'b55496ac7940a7ae47d2c01eab40edfd8701feec1229d9cce3b40014383fb828') then
    RaiseException('The Whisper model is required. Setup was cancelled.');
  if not Fetch('the Whisper tokenizer', HfWhisper + 'tokenizer.json', 'w_tokenizer.json',
       'fb7b63191e9bb045082c79fd742a3106a12c99513ab30df4a0d47fa6cb6fd0ab') then
    RaiseException('The Whisper model is required. Setup was cancelled.');
  if not Fetch('the Whisper vocabulary', HfWhisper + 'vocabulary.txt', 'w_vocabulary.txt',
       '34ce3fe1c5041027b3f8d42912270993f986dbc4bb34cf27f951e34a1e453913') then
    RaiseException('The Whisper model is required. Setup was cancelled.');
  PlaceFile('w_model.bin', Dir, 'model.bin');
  PlaceFile('w_config.json', Dir, 'config.json');
  PlaceFile('w_tokenizer.json', Dir, 'tokenizer.json');
  PlaceFile('w_vocabulary.txt', Dir, 'vocabulary.txt');
end;

procedure InstallTesseract;
var
  ResultCode: Integer;
begin
  if not WizardIsTaskSelected('tesseract') then Exit;
  if not NeedTesseract then Exit;
  if not Fetch('Tesseract OCR (27 MB)', TesseractUrl, 'tesseract-setup.exe', TesseractSha) then
  begin
    SuppressibleMsgBox('Tesseract was skipped. "click on ..." will not work until you install it from ' +
      'https://github.com/UB-Mannheim/tesseract/wiki', mbInformation, MB_OK, IDOK);
    Exit;
  end;
  WizardForm.StatusLabel.Caption := 'Installing Tesseract OCR (approve the administrator prompt) ...';
  if not ShellExec('runas', ExpandConstant('{tmp}\tesseract-setup.exe'), '/S', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
    SuppressibleMsgBox('Tesseract was not installed (administrator permission was declined).', mbInformation, MB_OK, IDOK);
end;

function OllamaInstalled: Boolean;
begin
  Result := FileExists(ExpandConstant('{localappdata}\Programs\Ollama\ollama.exe'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    InstallVosk;
    InstallPiper;
    InstallWhisper;
    InstallTesseract;
  end;
  if (CurStep = ssDone) and not OllamaInstalled then
    SuppressibleMsgBox('Ollama was not found on this PC. The assistant needs it for general AI answers:' + NL + NL +
      '1. Install it from https://ollama.com/download' + NL +
      '2. Run:  ollama pull qwen2.5:7b', mbInformation, MB_OK, IDOK);
end;
