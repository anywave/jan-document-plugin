use serde::{Deserialize, Serialize};
use std::io::{BufRead, BufReader, Read};
use std::path::PathBuf;
use std::process::{Command, Stdio};
use tauri::{AppHandle, Emitter, Manager};
use zip::ZipArchive;

/// Response from Python document processor
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DocumentProcessResult {
    pub success: bool,
    pub file_path: String,
    pub chunks_created: usize,
    pub error: Option<String>,
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
    app_handle
        .path()
        .resource_dir()
        .expect("Failed to get resource dir")
        .join("python312.zip")
}

/// Get path to the bundled Python executable
fn get_python_exe(app_handle: &AppHandle) -> PathBuf {
    get_python_dir(app_handle).join("python.exe")
}

/// Get path to the bundled Python scripts directory
fn get_python_scripts_path(app_handle: &AppHandle) -> PathBuf {
    get_python_dir(app_handle).join("scripts")
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
    let mut archive = ZipArchive::new(file)
        .map_err(|e| format!("Failed to read Python archive: {}", e))?;

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i)
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

/// Execute Python command and return JSON result
async fn execute_python_command(
    app_handle: AppHandle,
    script_name: &str,
    args: Vec<String>,
) -> Result<String, String> {
    // Ensure Python is extracted from the bundled zip on first use
    ensure_python_extracted(&app_handle)?;

    let python_exe = get_python_exe(&app_handle);
    let script_path = get_python_scripts_path(&app_handle).join(script_name);

    if !python_exe.exists() {
        return Err(format!("Bundled Python not found: {:?}", python_exe));
    }

    if !script_path.exists() {
        return Err(format!("Python script not found: {:?}", script_path));
    }

    log::info!("Executing Python script: {:?} with args: {:?}", script_path, args);

    // Spawn bundled Python process
    let mut child = Command::new(&python_exe)
        .arg(&script_path)
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("Failed to spawn Python process: {}", e))?;

    // Read stdout
    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| "Failed to capture stdout".to_string())?;
    let mut reader = BufReader::new(stdout);

    // Collect output
    let mut output = String::new();
    let mut line = String::new();
    while reader.read_line(&mut line).map_err(|e| e.to_string())? > 0 {
        output.push_str(&line);
        line.clear();
    }

    // Wait for process to complete
    let status = child.wait().map_err(|e| e.to_string())?;

    if !status.success() {
        // Read stderr for error details
        let stderr = child
            .stderr
            .take()
            .ok_or_else(|| "Failed to capture stderr".to_string())?;
        let mut err_reader = BufReader::new(stderr);
        let mut error_output = String::new();
        err_reader
            .read_to_string(&mut error_output)
            .map_err(|e: std::io::Error| e.to_string())?;

        return Err(format!(
            "Python process failed with exit code {:?}: {}",
            status.code(),
            error_output
        ));
    }

    Ok(output)
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
            error: Some(format!(
                "Bundled Python not found at: {:?}",
                python_exe
            )),
        });
    }

    // Check bundled Python version
    let python_check = Command::new(&python_exe)
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
            error: Some(format!(
                "Python scripts not found at: {:?}",
                script_path
            )),
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
) -> Result<DocumentProcessResult, String> {
    log::info!("Processing document: {}", file_path);

    // Emit progress event
    let _ = app_handle.emit("document-processing",
        serde_json::json!({"status": "starting", "file": &file_path}));

    // Build command args
    let mut args = vec![
        "--json".to_string(),  // Enable JSON output
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

    // Execute Python script
    let output = execute_python_command(
        app_handle.clone(),
        "document_processor.py",
        args,
    )
    .await?;

    // Parse output (Python prints JSON to stdout)
    let result: DocumentProcessResult = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse Python output: {}", e))?;

    // Emit completion event
    let status = if result.success { "complete" } else { "failed" };
    let _ = app_handle.emit("document-processing",
        serde_json::json!({
            "status": status,
            "file": &file_path,
            "chunks": result.chunks_created,
            "error": result.error
        }));

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
    let args = vec![
        "--json".to_string(),  // Enable JSON output
        "query".to_string(),
        query.clone(),
        "--collection".to_string(),
        collection_name.unwrap_or_else(|| "documents".to_string()),
        "--top-k".to_string(),
        top_k.unwrap_or(5).to_string(),
    ];

    // Execute Python script
    let output = execute_python_command(
        app_handle,
        "document_processor.py",
        args,
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
    let args = vec![
        "--json".to_string(),  // Enable JSON output
        "stats".to_string(),
        "--collection".to_string(),
        collection_name.unwrap_or_else(|| "documents".to_string()),
    ];

    // Execute Python script
    let output = execute_python_command(
        app_handle,
        "document_processor.py",
        args,
    )
    .await?;

    // Parse output
    let result: CollectionStats = serde_json::from_str(&output)
        .map_err(|e| format!("Failed to parse Python output: {}", e))?;

    Ok(result)
}
