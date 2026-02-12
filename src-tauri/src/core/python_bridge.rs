use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::time::Duration;
use tauri::{AppHandle, Emitter, Manager};
use tokio::io::{AsyncBufReadExt, AsyncReadExt, BufReader};
use tokio::process::Command;
use zip::ZipArchive;

// --- Constants for timeout & retry ---
const PYTHON_COMMAND_TIMEOUT: Duration = Duration::from_secs(60);
const PYTHON_EXTRACTION_TIMEOUT: Duration = Duration::from_secs(300);
const PYTHON_MAX_RETRIES: u32 = 3;
const PYTHON_BASE_DELAY_MS: u64 = 1000;
const PYTHON_MAX_DELAY_MS: u64 = 15000;
const PYTHON_BACKOFF_MULTIPLIER: f64 = 2.0;

// --- Allowed file extensions (defense-in-depth) ---
const ALLOWED_EXTENSIONS: &[&str] = &[".txt", ".md", ".doc", ".docx", ".rtf"];

/// Response from Python document processor
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DocumentProcessResult {
    pub success: bool,
    pub file_path: String,
    pub chunks_created: usize,
    pub error: Option<String>,
    pub processing_time: Option<f64>,
    pub document_summary: Option<DocumentSummary>,
}

/// Rich document summary returned after processing
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DocumentSummary {
    pub file_name: String,
    pub file_size_bytes: u64,
    pub file_size_mb: f64,
    pub word_count: usize,
    pub char_count: usize,
    pub chunks_created: usize,
    pub sections_detected: Vec<String>,
    pub preview: String,
    pub processing_time: f64,
}

/// Response from Python query
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct QueryResult {
    pub query: String,
    pub results: Vec<QueryMatch>,
    pub error: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct QueryMatch {
    pub id: String,
    pub text: String,
    pub metadata: serde_json::Value,
    pub distance: f64,
}

/// Collection statistics
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct CollectionStats {
    pub collection: String,
    pub document_count: usize,
    pub all_collections: Vec<String>,
}

/// Python environment check result
#[derive(Debug, Serialize, Deserialize)]
pub struct PythonStatus {
    pub available: bool,
    pub version: Option<String>,
    pub script_path: Option<String>,
    pub error: Option<String>,
}

/// ChromaDB health check result
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChromaDbHealth {
    pub healthy: bool,
    pub document_count: usize,
    pub error: Option<String>,
    pub recovered: bool,
}

/// Structured error event payload
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct PythonErrorEvent {
    pub error_type: String,
    pub message: String,
    pub attempt: u32,
    pub max_attempts: u32,
}

/// Jan lock status result
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct JanLockStatus {
    pub jan_installed: bool,
    pub jan_version: Option<String>,
    pub jan_install_path: Option<String>,
    pub mobius_locked: bool,
}

/// A scanned file entry from directory scanning
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ScannedFile {
    pub path: String,
    pub name: String,
    pub size: u64,
    pub extension: String,
}

/// Result of scanning a directory for processable files
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ScanDirectoryResult {
    pub files: Vec<ScannedFile>,
    pub total_size: u64,
    pub skipped: usize,
}

/// Per-file result emitted during batch processing (from stderr)
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BatchFileResult {
    pub file_path: String,
    pub file_name: String,
    pub success: bool,
    pub chunks_created: usize,
    pub error: Option<String>,
    pub processing_time: f64,
    pub batch_index: usize,
    pub batch_total: usize,
}

/// Aggregate result from batch processing (from stdout)
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BatchProcessResult {
    pub results: Vec<DocumentProcessResult>,
    pub success_count: usize,
    pub error_count: usize,
    pub total_files: usize,
    pub total_time: f64,
}

/// Get path to the extracted Python 3.12 directory (in app data)
fn get_python_dir(app_handle: &AppHandle) -> PathBuf {
    app_handle
        .path()
        .app_data_dir()
        .expect("Failed to get app data dir")
        .join("python312")
}

/// Get path to the bundled Python zip archive (in resources)
fn get_python_zip_path(app_handle: &AppHandle) -> PathBuf {
    let resource_dir = app_handle
        .path()
        .resource_dir()
        .expect("Failed to get resource dir");
    let direct = resource_dir.join("python312.zip");
    if direct.exists() {
        return direct;
    }
    // In dev mode, resources are nested under a resources/ subdirectory
    resource_dir.join("resources").join("python312.zip")
}

/// Get path to the bundled Python executable
fn get_python_exe(app_handle: &AppHandle) -> PathBuf {
    get_python_dir(app_handle).join("python.exe")
}

/// Get path to the bundled Python scripts directory
fn get_python_scripts_path(app_handle: &AppHandle) -> PathBuf {
    get_python_dir(app_handle).join("scripts")
}

/// Get path to the ChromaDB persistence directory (in app data, not source tree)
fn get_chromadb_dir(app_handle: &AppHandle) -> PathBuf {
    app_handle
        .path()
        .app_data_dir()
        .expect("Failed to get app data dir")
        .join("chroma_db")
}

// --- Input Validation (Phase 1B) ---

/// Validate a file path: reject path traversal and shell metacharacters
fn validate_file_path(file_path: &str) -> Result<(), String> {
    // Reject path traversal
    if file_path.contains("..") {
        return Err("Invalid file path: path traversal detected".to_string());
    }

    // Reject shell metacharacters
    const DANGEROUS_CHARS: &[char] = &['|', ';', '&', '$', '`', '>', '<', '!', '{', '}'];
    for ch in DANGEROUS_CHARS {
        if file_path.contains(*ch) {
            return Err(format!(
                "Invalid file path: forbidden character '{}' detected",
                ch
            ));
        }
    }

    // Restrict to allowed extensions (defense-in-depth)
    let path = Path::new(file_path);
    if let Some(ext) = path.extension() {
        let ext_str = format!(".{}", ext.to_string_lossy().to_lowercase());
        if !ALLOWED_EXTENSIONS.contains(&ext_str.as_str()) {
            return Err(format!(
                "Unsupported file type '{}'. Only {} are allowed.",
                ext_str,
                ALLOWED_EXTENSIONS.join(", ")
            ));
        }
    } else {
        return Err("File has no extension. Only .txt and .md are allowed.".to_string());
    }

    Ok(())
}

/// Sanitize all Python arguments: reject dangerous characters
fn sanitize_python_args(args: &[String]) -> Result<(), String> {
    const DANGEROUS_CHARS: &[char] = &['|', ';', '&', '$', '`'];
    for arg in args {
        for ch in DANGEROUS_CHARS {
            if arg.contains(*ch) {
                return Err(format!(
                    "Invalid argument: forbidden character '{}' detected in '{}'",
                    ch, arg
                ));
            }
        }
    }
    Ok(())
}

// --- Exponential Backoff (reuses pattern from mcp.rs) ---

/// Calculate exponential backoff delay with jitter
fn calculate_python_backoff_delay(attempt: u32) -> u64 {
    use std::cmp;

    let exponential_delay =
        (PYTHON_BASE_DELAY_MS as f64) * PYTHON_BACKOFF_MULTIPLIER.powi((attempt - 1) as i32);

    let capped_delay = cmp::min(exponential_delay as u64, PYTHON_MAX_DELAY_MS);

    // Add jitter (+-25%) to prevent thundering herd
    let jitter_range = (capped_delay as f64 * 0.25) as u64;
    let jitter = if jitter_range > 0 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        attempt.hash(&mut hasher);
        let hash = hasher.finish();

        (hash % (jitter_range * 2)) as i64 - jitter_range as i64
    } else {
        0
    };

    cmp::max(
        100,
        cmp::min(PYTHON_MAX_DELAY_MS, (capped_delay as i64 + jitter) as u64),
    )
}

/// Ensure Python is extracted from the bundled zip archive.
/// Extracts only on first run or if python.exe is missing.
fn ensure_python_extracted(app_handle: &AppHandle) -> Result<(), String> {
    let python_dir = get_python_dir(app_handle);
    let python_exe = python_dir.join("python.exe");

    // Already extracted
    if python_exe.exists() {
        return Ok(());
    }

    let zip_path = get_python_zip_path(app_handle);
    if !zip_path.exists() {
        return Err(format!(
            "Python archive not found at: {:?}. Reinstall MOBIUS.",
            zip_path
        ));
    }

    log::info!("Extracting bundled Python to {:?}...", python_dir);

    // Create target directory
    std::fs::create_dir_all(&python_dir)
        .map_err(|e| format!("Failed to create Python directory: {}", e))?;

    // Extract zip
    let file = std::fs::File::open(&zip_path)
        .map_err(|e| format!("Failed to open Python archive: {}", e))?;
    let mut archive =
        ZipArchive::new(file).map_err(|e| format!("Failed to read Python archive: {}", e))?;

    for i in 0..archive.len() {
        let mut entry = archive
            .by_index(i)
            .map_err(|e| format!("Failed to read archive entry: {}", e))?;

        let outpath = python_dir.join(entry.mangled_name());

        if entry.is_dir() {
            std::fs::create_dir_all(&outpath)
                .map_err(|e| format!("Failed to create directory {:?}: {}", outpath, e))?;
        } else {
            if let Some(parent) = outpath.parent() {
                std::fs::create_dir_all(parent)
                    .map_err(|e| format!("Failed to create parent dir: {}", e))?;
            }
            let mut outfile = std::fs::File::create(&outpath)
                .map_err(|e| format!("Failed to create file {:?}: {}", outpath, e))?;
            std::io::copy(&mut entry, &mut outfile)
                .map_err(|e| format!("Failed to extract {:?}: {}", outpath, e))?;
        }
    }

    log::info!("Python extraction complete ({} entries)", archive.len());
    Ok(())
}

/// Execute Python command with timeout using tokio::process::Command
async fn execute_python_command(
    app_handle: &AppHandle,
    script_name: &str,
    args: Vec<String>,
    timeout: Duration,
) -> Result<String, String> {
    // Ensure Python is extracted from the bundled zip on first use
    ensure_python_extracted(app_handle)?;

    // Sanitize all args
    sanitize_python_args(&args)?;

    let python_exe = get_python_exe(app_handle);
    let script_path = get_python_scripts_path(app_handle).join(script_name);

    if !python_exe.exists() {
        return Err(format!("Bundled Python not found: {:?}", python_exe));
    }

    if !script_path.exists() {
        return Err(format!("Python script not found: {:?}", script_path));
    }

    log::info!(
        "Executing Python script: {:?} with args: {:?}",
        script_path,
        args
    );

    // Spawn bundled Python process using tokio::process::Command for async timeout+kill
    let mut child = Command::new(&python_exe)
        .arg(&script_path)
        .args(&args)
        .stdin(std::process::Stdio::null())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::piped())
        .kill_on_drop(true)
        .spawn()
        .map_err(|e| format!("Failed to spawn Python process: {}", e))?;

    // Take stdout and stderr handles
    let mut stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Failed to capture stdout".to_string())?;
    let stderr = child
        .stderr
        .take()
        .ok_or_else(|| "Failed to capture stderr".to_string())?;

    // Stream stderr line-by-line for real-time progress, collect stdout for final result
    let app_for_stderr = app_handle.clone();
    let result = tokio::time::timeout(timeout, async {
        let mut stdout_buf = String::new();
        let mut stderr_buf = String::new();

        // Read stderr line-by-line and emit progress events in real-time
        let stderr_task = tokio::spawn(async move {
            let reader = BufReader::new(stderr);
            let mut lines = reader.lines();
            let mut collected = String::new();

            while let Ok(Some(line)) = lines.next_line().await {
                // Try to parse as JSON from Python
                if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&line) {
                    if parsed.get("progress").and_then(|v| v.as_bool()) == Some(true) {
                        let _ = app_for_stderr.emit("document-processing", &parsed);
                        continue;
                    }
                    if parsed.get("file_result").and_then(|v| v.as_bool()) == Some(true) {
                        let _ = app_for_stderr.emit("batch-file-result", &parsed);
                        continue;
                    }
                }
                // Non-progress stderr lines collected for error reporting
                if !collected.is_empty() {
                    collected.push('\n');
                }
                collected.push_str(&line);
            }
            collected
        });

        let stdout_result = stdout.read_to_string(&mut stdout_buf).await;
        stdout_result.map_err(|e| format!("Failed to read stdout: {}", e))?;

        stderr_buf = stderr_task
            .await
            .map_err(|e| format!("stderr task failed: {}", e))?;

        let status = child.wait().await.map_err(|e| e.to_string())?;

        if !status.success() {
            return Err(format!(
                "Python process failed with exit code {:?}: {}",
                status.code(),
                stderr_buf
            ));
        }

        Ok(stdout_buf)
    })
    .await;

    match result {
        Ok(inner) => inner,
        Err(_) => {
            // Timeout elapsed — child is killed on drop
            Err(format!(
                "Python command timed out after {}s",
                timeout.as_secs()
            ))
        }
    }
}

/// Execute Python command with retry and exponential backoff
async fn execute_python_command_with_retry(
    app_handle: &AppHandle,
    script_name: &str,
    args: Vec<String>,
    timeout: Duration,
) -> Result<String, String> {
    let mut last_error = String::new();

    for attempt in 1..=PYTHON_MAX_RETRIES {
        match execute_python_command(app_handle, script_name, args.clone(), timeout).await {
            Ok(output) => return Ok(output),
            Err(e) => {
                last_error = e.clone();
                log::warn!(
                    "Python command attempt {}/{} failed: {}",
                    attempt,
                    PYTHON_MAX_RETRIES,
                    e
                );

                // Emit structured error event
                let _ = app_handle.emit(
                    "python-error",
                    PythonErrorEvent {
                        error_type: if e.contains("timed out") {
                            "timeout".to_string()
                        } else if e.contains("Failed to spawn") {
                            "spawn_error".to_string()
                        } else {
                            "execution_error".to_string()
                        },
                        message: e,
                        attempt,
                        max_attempts: PYTHON_MAX_RETRIES,
                    },
                );

                if attempt < PYTHON_MAX_RETRIES {
                    let delay = calculate_python_backoff_delay(attempt);
                    log::info!("Retrying in {}ms...", delay);
                    tokio::time::sleep(Duration::from_millis(delay)).await;
                }
            }
        }
    }

    Err(format!(
        "Python command failed after {} attempts: {}",
        PYTHON_MAX_RETRIES, last_error
    ))
}

/// Check if bundled Python is available and scripts are installed
#[tauri::command]
pub async fn check_python_status(app_handle: AppHandle) -> Result<PythonStatus, String> {
    log::info!("Checking Python status...");

    // Ensure Python is extracted from the bundled zip on first use
    if let Err(e) = ensure_python_extracted(&app_handle) {
        return Ok(PythonStatus {
            available: false,
            version: None,
            script_path: None,
            error: Some(format!("Failed to extract Python: {}", e)),
        });
    }

    let python_exe = get_python_exe(&app_handle);

    // Check if bundled Python exists
    if !python_exe.exists() {
        return Ok(PythonStatus {
            available: false,
            version: None,
            script_path: None,
            error: Some(format!("Bundled Python not found at: {:?}", python_exe)),
        });
    }

    // Check bundled Python version
    let python_check = std::process::Command::new(&python_exe)
        .arg("--version")
        .output();

    let version = match python_check {
        Ok(output) if output.status.success() => {
            let version_str = String::from_utf8_lossy(&output.stdout);
            Some(version_str.trim().to_string())
        }
        _ => None,
    };

    // Check if scripts exist
    let script_path = get_python_scripts_path(&app_handle);
    let main_script = script_path.join("document_processor.py");

    if !main_script.exists() {
        return Ok(PythonStatus {
            available: true,
            version,
            script_path: Some(script_path.to_string_lossy().to_string()),
            error: Some(format!("Python scripts not found at: {:?}", script_path)),
        });
    }

    Ok(PythonStatus {
        available: true,
        version,
        script_path: Some(script_path.to_string_lossy().to_string()),
        error: None,
    })
}

/// Process a document: extract, chunk, embed, and store
#[tauri::command]
pub async fn process_document(
    app_handle: AppHandle,
    file_path: String,
    collection_name: Option<String>,
    use_ocr: Option<bool>,
    password: Option<String>,
    smart: Option<bool>,
) -> Result<DocumentProcessResult, String> {
    log::info!("Processing document: {}", file_path);

    // Validate file path (Phase 1B — defense-in-depth)
    validate_file_path(&file_path)?;

    // Emit progress event
    let _ = app_handle.emit(
        "document-processing",
        serde_json::json!({"status": "starting", "file": &file_path}),
    );

    // Build command args — pass app data dir for ChromaDB so it doesn't write to source tree
    let db_path = get_chromadb_dir(&app_handle);
    let mut args = vec![
        "--json".to_string(),
        "--db-path".to_string(),
        db_path.to_string_lossy().to_string(),
        "process".to_string(),
        file_path.clone(),
        "--collection".to_string(),
        collection_name.unwrap_or_else(|| "documents".to_string()),
    ];

    if let Some(false) = use_ocr {
        args.push("--no-ocr".to_string());
    }

    if let Some(pwd) = password {
        args.push("--password".to_string());
        args.push(pwd);
    }

    if smart.unwrap_or(false) {
        args.push("--smart".to_string());
    }

    // Execute Python script with retry and extraction timeout
    let output = execute_python_command_with_retry(
        &app_handle,
        "document_processor.py",
        args,
        PYTHON_EXTRACTION_TIMEOUT,
    )
    .await?;

    // Parse output (Python prints JSON to stdout)
    let result: DocumentProcessResult = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse Python output: {}", e))?;

    // Emit completion event
    let status = if result.success { "complete" } else { "failed" };
    let _ = app_handle.emit(
        "document-processing",
        serde_json::json!({
            "status": status,
            "file": &file_path,
            "chunks": result.chunks_created,
            "error": result.error
        }),
    );

    Ok(result)
}

/// Query indexed documents
#[tauri::command]
pub async fn query_documents(
    app_handle: AppHandle,
    query: String,
    collection_name: Option<String>,
    top_k: Option<usize>,
) -> Result<QueryResult, String> {
    log::info!("Querying documents: {}", query);

    // Build command args
    let db_path = get_chromadb_dir(&app_handle);
    let args = vec![
        "--json".to_string(),
        "--db-path".to_string(),
        db_path.to_string_lossy().to_string(),
        "query".to_string(),
        query.clone(),
        "--collection".to_string(),
        collection_name.unwrap_or_else(|| "documents".to_string()),
        "--top-k".to_string(),
        top_k.unwrap_or(5).to_string(),
    ];

    // Execute Python script with retry
    let output = execute_python_command_with_retry(
        &app_handle,
        "document_processor.py",
        args,
        PYTHON_COMMAND_TIMEOUT,
    )
    .await?;

    // Parse output
    let result: QueryResult = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse Python output: {}", e))?;

    Ok(result)
}

/// Get collection statistics
#[tauri::command]
pub async fn get_collection_stats(
    app_handle: AppHandle,
    collection_name: Option<String>,
) -> Result<CollectionStats, String> {
    log::info!("Getting collection stats");

    // Build command args
    let db_path = get_chromadb_dir(&app_handle);
    let args = vec![
        "--json".to_string(),
        "--db-path".to_string(),
        db_path.to_string_lossy().to_string(),
        "stats".to_string(),
        "--collection".to_string(),
        collection_name.unwrap_or_else(|| "documents".to_string()),
    ];

    // Execute Python script with retry
    let output = execute_python_command_with_retry(
        &app_handle,
        "document_processor.py",
        args,
        PYTHON_COMMAND_TIMEOUT,
    )
    .await?;

    // Parse output
    let result: CollectionStats = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse Python output: {}", e))?;

    Ok(result)
}

/// Check ChromaDB health status
#[tauri::command]
pub async fn check_chromadb_health(
    app_handle: AppHandle,
    collection_name: Option<String>,
    auto_recover: Option<bool>,
) -> Result<ChromaDbHealth, String> {
    log::info!("Checking ChromaDB health");

    let db_path = get_chromadb_dir(&app_handle);
    let mut args = vec![
        "--json".to_string(),
        "--db-path".to_string(),
        db_path.to_string_lossy().to_string(),
        "health".to_string(),
        "--collection".to_string(),
        collection_name.unwrap_or_else(|| "documents".to_string()),
    ];

    if auto_recover.unwrap_or(false) {
        args.push("--auto-recover".to_string());
    }

    let output = execute_python_command_with_retry(
        &app_handle,
        "document_processor.py",
        args,
        PYTHON_COMMAND_TIMEOUT,
    )
    .await?;

    let result: ChromaDbHealth = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse ChromaDB health output: {}", e))?;

    Ok(result)
}

/// Check Jan lock status by reading Windows registry
#[tauri::command]
pub async fn check_jan_lock_status() -> Result<JanLockStatus, String> {
    #[cfg(windows)]
    {
        use windows_sys::Win32::System::Registry::*;

        let mut status = JanLockStatus {
            jan_installed: false,
            jan_version: None,
            jan_install_path: None,
            mobius_locked: false,
        };

        // Check for Jan installation in HKCU uninstall keys
        let jan_key_path = "Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\jan\0"
            .encode_utf16()
            .collect::<Vec<u16>>();

        let mut hkey: HKEY = std::ptr::null_mut();
        let result = unsafe {
            RegOpenKeyExW(
                HKEY_CURRENT_USER,
                jan_key_path.as_ptr(),
                0,
                KEY_READ,
                &mut hkey,
            )
        };

        if result == 0 {
            status.jan_installed = true;

            // Read InstallLocation
            let mut buf = [0u16; 512];
            let mut buf_size = (buf.len() * 2) as u32;
            let value_name = "InstallLocation\0".encode_utf16().collect::<Vec<u16>>();
            let read_result = unsafe {
                RegQueryValueExW(
                    hkey,
                    value_name.as_ptr(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    buf.as_mut_ptr() as *mut u8,
                    &mut buf_size,
                )
            };
            if read_result == 0 {
                let len = (buf_size as usize / 2).saturating_sub(1);
                status.jan_install_path = Some(String::from_utf16_lossy(&buf[..len]));
            }

            // Read DisplayVersion
            let mut buf2 = [0u16; 256];
            let mut buf2_size = (buf2.len() * 2) as u32;
            let ver_name = "DisplayVersion\0".encode_utf16().collect::<Vec<u16>>();
            let ver_result = unsafe {
                RegQueryValueExW(
                    hkey,
                    ver_name.as_ptr(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    buf2.as_mut_ptr() as *mut u8,
                    &mut buf2_size,
                )
            };
            if ver_result == 0 {
                let len = (buf2_size as usize / 2).saturating_sub(1);
                status.jan_version = Some(String::from_utf16_lossy(&buf2[..len]));
            }

            unsafe { RegCloseKey(hkey) };
        } else {
            // Try HKLM as fallback
            let result_lm = unsafe {
                RegOpenKeyExW(
                    HKEY_LOCAL_MACHINE,
                    jan_key_path.as_ptr(),
                    0,
                    KEY_READ,
                    &mut hkey,
                )
            };
            if result_lm == 0 {
                status.jan_installed = true;
                unsafe { RegCloseKey(hkey) };
            }
        }

        // Check MOBIUS lock status
        let mobius_key_path = "Software\\ANYWAVE\\MOBIUS\0"
            .encode_utf16()
            .collect::<Vec<u16>>();
        let mut mobius_hkey: HKEY = std::ptr::null_mut();
        let mobius_result = unsafe {
            RegOpenKeyExW(
                HKEY_CURRENT_USER,
                mobius_key_path.as_ptr(),
                0,
                KEY_READ,
                &mut mobius_hkey,
            )
        };

        if mobius_result == 0 {
            let mut lock_value: u32 = 0;
            let mut lock_size = std::mem::size_of::<u32>() as u32;
            let lock_name = "JanLocked\0".encode_utf16().collect::<Vec<u16>>();
            let lock_result = unsafe {
                RegQueryValueExW(
                    mobius_hkey,
                    lock_name.as_ptr(),
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    &mut lock_value as *mut u32 as *mut u8,
                    &mut lock_size,
                )
            };
            if lock_result == 0 && lock_value == 1 {
                status.mobius_locked = true;
            }
            unsafe { RegCloseKey(mobius_hkey) };
        }

        Ok(status)
    }

    #[cfg(not(windows))]
    {
        Ok(JanLockStatus {
            jan_installed: false,
            jan_version: None,
            jan_install_path: None,
            mobius_locked: false,
        })
    }
}

/// Scan a directory for processable document files (pure Rust, no Python)
#[tauri::command]
pub async fn scan_directory(directory_path: String) -> Result<ScanDirectoryResult, String> {
    log::info!("Scanning directory: {}", directory_path);

    let dir = Path::new(&directory_path);
    if !dir.is_dir() {
        return Err(format!("Not a directory: {}", directory_path));
    }

    let mut files = Vec::new();
    let mut total_size: u64 = 0;
    let mut skipped: usize = 0;

    fn walk_dir(
        dir: &Path,
        files: &mut Vec<ScannedFile>,
        total_size: &mut u64,
        skipped: &mut usize,
    ) -> Result<(), String> {
        let entries =
            std::fs::read_dir(dir).map_err(|e| format!("Failed to read directory: {}", e))?;

        for entry in entries {
            let entry = entry.map_err(|e| format!("Failed to read entry: {}", e))?;
            let path = entry.path();

            if path.is_dir() {
                walk_dir(&path, files, total_size, skipped)?;
            } else if path.is_file() {
                if let Some(ext) = path.extension() {
                    let ext_str = format!(".{}", ext.to_string_lossy().to_lowercase());
                    if ALLOWED_EXTENSIONS.contains(&ext_str.as_str()) {
                        let metadata = std::fs::metadata(&path)
                            .map_err(|e| format!("Failed to get metadata: {}", e))?;
                        let size = metadata.len();
                        *total_size += size;
                        files.push(ScannedFile {
                            path: path.to_string_lossy().to_string(),
                            name: path
                                .file_name()
                                .map(|n| n.to_string_lossy().to_string())
                                .unwrap_or_default(),
                            size,
                            extension: ext_str,
                        });
                    } else {
                        *skipped += 1;
                    }
                } else {
                    *skipped += 1;
                }
            }
        }
        Ok(())
    }

    walk_dir(dir, &mut files, &mut total_size, &mut skipped)?;

    // Sort by name for consistent ordering
    files.sort_by(|a, b| a.name.to_lowercase().cmp(&b.name.to_lowercase()));

    Ok(ScanDirectoryResult {
        files,
        total_size,
        skipped,
    })
}

/// Process multiple documents in a single batch (model loaded once)
#[tauri::command]
pub async fn process_document_batch(
    app_handle: AppHandle,
    file_paths: Vec<String>,
    collection_name: Option<String>,
    smart: Option<bool>,
) -> Result<BatchProcessResult, String> {
    let file_count = file_paths.len();
    log::info!("Processing batch of {} documents", file_count);

    if file_paths.is_empty() {
        return Err("No files provided for batch processing".to_string());
    }

    // Validate all file paths upfront
    for fp in &file_paths {
        validate_file_path(fp)?;
    }

    // Emit batch starting event
    let _ = app_handle.emit(
        "document-processing",
        serde_json::json!({
            "status": "starting",
            "batch_total": file_count,
        }),
    );

    // Build command args
    let db_path = get_chromadb_dir(&app_handle);
    let mut args = vec![
        "--json".to_string(),
        "--db-path".to_string(),
        db_path.to_string_lossy().to_string(),
        "batch".to_string(),
        "--files".to_string(),
    ];
    args.extend(file_paths.clone());
    args.push("--collection".to_string());
    args.push(collection_name.unwrap_or_else(|| "documents".to_string()));

    if smart.unwrap_or(false) {
        args.push("--smart".to_string());
    }

    // Dynamic timeout: 300s base + 120s per file, capped at 1 hour
    let timeout_secs = std::cmp::min(300 + 120 * file_count as u64, 3600);
    let timeout = Duration::from_secs(timeout_secs);

    // Execute Python batch command (no retry — batch is not idempotent mid-run)
    let output =
        execute_python_command(&app_handle, "document_processor.py", args, timeout).await?;

    // Parse aggregate result
    let result: BatchProcessResult = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse batch output: {}", e))?;

    // Emit batch completion event
    let _ = app_handle.emit(
        "document-processing",
        serde_json::json!({
            "status": "complete",
            "batch_total": result.total_files,
            "success_count": result.success_count,
            "error_count": result.error_count,
            "total_time": result.total_time,
        }),
    );

    Ok(result)
}
