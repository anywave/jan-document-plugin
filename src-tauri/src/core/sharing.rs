/*!
    .mobius Package Sharing Module

    Handles creation, reading, and importing of .mobius packages (zip archives)
    containing assistants, threads, messages, and knowledge chunks.
*/

use serde_json::Value;
use std::fs::{self, File};
use std::io::{Read, Write};
use tauri::command;
use tauri::Runtime;
use zip::write::SimpleFileOptions;

use super::cmd::get_jan_data_folder_path;

/// Creates a .mobius package (zip file) from the provided JSON data.
///
/// # Arguments
/// * `output_path` - Where to write the .mobius file
/// * `manifest` - Package manifest JSON
/// * `assistants` - Array of sanitized assistant JSONs
/// * `threads` - Array of { thread, messages } objects
/// * `knowledge` - Array of knowledge chunk JSONs
#[command]
pub async fn create_mobius_package<R: Runtime>(
    _app_handle: tauri::AppHandle<R>,
    output_path: String,
    manifest: Value,
    assistants: Vec<Value>,
    threads: Vec<Value>,
    knowledge: Vec<Value>,
) -> Result<String, String> {
    let file = File::create(&output_path).map_err(|e| format!("Failed to create file: {}", e))?;
    let mut zip = zip::ZipWriter::new(file);
    let options = SimpleFileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    // Write manifest
    let manifest_str =
        serde_json::to_string_pretty(&manifest).map_err(|e| format!("JSON error: {}", e))?;
    zip.start_file("manifest.json", options)
        .map_err(|e| format!("Zip error: {}", e))?;
    zip.write_all(manifest_str.as_bytes())
        .map_err(|e| format!("Write error: {}", e))?;

    // Write assistants
    for assistant in &assistants {
        let id = assistant
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");
        let data = serde_json::to_string_pretty(assistant)
            .map_err(|e| format!("JSON error: {}", e))?;
        zip.start_file(format!("assistants/{}.json", id), options)
            .map_err(|e| format!("Zip error: {}", e))?;
        zip.write_all(data.as_bytes())
            .map_err(|e| format!("Write error: {}", e))?;
    }

    // Write threads and their messages
    for entry in &threads {
        let thread = entry.get("thread").ok_or("Missing thread in entry")?;
        let messages = entry.get("messages").ok_or("Missing messages in entry")?;

        let thread_id = thread
            .get("id")
            .and_then(|v| v.as_str())
            .unwrap_or("unknown");

        // Thread metadata
        let thread_data =
            serde_json::to_string_pretty(thread).map_err(|e| format!("JSON error: {}", e))?;
        zip.start_file(format!("threads/{}/thread.json", thread_id), options)
            .map_err(|e| format!("Zip error: {}", e))?;
        zip.write_all(thread_data.as_bytes())
            .map_err(|e| format!("Write error: {}", e))?;

        // Messages as JSONL
        if let Some(msgs) = messages.as_array() {
            let mut jsonl = String::new();
            for msg in msgs {
                let line =
                    serde_json::to_string(msg).map_err(|e| format!("JSON error: {}", e))?;
                jsonl.push_str(&line);
                jsonl.push('\n');
            }
            zip.start_file(format!("threads/{}/messages.jsonl", thread_id), options)
                .map_err(|e| format!("Zip error: {}", e))?;
            zip.write_all(jsonl.as_bytes())
                .map_err(|e| format!("Write error: {}", e))?;
        }
    }

    // Write knowledge chunks grouped by collection
    if !knowledge.is_empty() {
        // Group by collection
        let mut collections: std::collections::HashMap<String, Vec<&Value>> =
            std::collections::HashMap::new();
        for chunk in &knowledge {
            let collection = chunk
                .get("collection")
                .and_then(|v| v.as_str())
                .unwrap_or("default")
                .to_string();
            collections.entry(collection).or_default().push(chunk);
        }

        for (collection, chunks) in &collections {
            let data = serde_json::to_string_pretty(chunks)
                .map_err(|e| format!("JSON error: {}", e))?;
            zip.start_file(format!("knowledge/{}/chunks.json", collection), options)
                .map_err(|e| format!("Zip error: {}", e))?;
            zip.write_all(data.as_bytes())
                .map_err(|e| format!("Write error: {}", e))?;
        }
    }

    zip.finish().map_err(|e| format!("Zip finalize error: {}", e))?;

    Ok(output_path)
}

/// Reads a .mobius package and returns its contents for preview.
///
/// Returns the manifest and a summary of contents without fully importing.
#[command]
pub async fn read_mobius_package<R: Runtime>(
    _app_handle: tauri::AppHandle<R>,
    package_path: String,
) -> Result<Value, String> {
    let file = File::open(&package_path)
        .map_err(|e| format!("Failed to open package: {}", e))?;
    let mut archive =
        zip::ZipArchive::new(file).map_err(|e| format!("Invalid .mobius package: {}", e))?;

    // Read manifest
    let manifest: Value = {
        let mut manifest_file = archive
            .by_name("manifest.json")
            .map_err(|_| "Package missing manifest.json".to_string())?;
        let mut contents = String::new();
        manifest_file
            .read_to_string(&mut contents)
            .map_err(|e| format!("Failed to read manifest: {}", e))?;
        serde_json::from_str(&contents).map_err(|e| format!("Invalid manifest JSON: {}", e))?
    };

    // Scan archive for contents
    let mut assistants: Vec<Value> = Vec::new();
    let mut threads: Vec<Value> = Vec::new();
    let mut knowledge_collections: Vec<Value> = Vec::new();

    for i in 0..archive.len() {
        let mut entry = archive.by_index(i).map_err(|e| format!("Zip error: {}", e))?;
        let name = entry.name().to_string();

        if name.starts_with("assistants/") && name.ends_with(".json") {
            let mut contents = String::new();
            entry
                .read_to_string(&mut contents)
                .map_err(|e| format!("Read error: {}", e))?;
            if let Ok(val) = serde_json::from_str::<Value>(&contents) {
                assistants.push(val);
            }
        } else if name.ends_with("/thread.json") && name.starts_with("threads/") {
            let mut contents = String::new();
            entry
                .read_to_string(&mut contents)
                .map_err(|e| format!("Read error: {}", e))?;
            if let Ok(val) = serde_json::from_str::<Value>(&contents) {
                threads.push(val);
            }
        } else if name.ends_with("/chunks.json") && name.starts_with("knowledge/") {
            let collection_name = name
                .strip_prefix("knowledge/")
                .and_then(|s| s.strip_suffix("/chunks.json"))
                .unwrap_or("unknown");
            let mut contents = String::new();
            entry
                .read_to_string(&mut contents)
                .map_err(|e| format!("Read error: {}", e))?;
            if let Ok(chunks) = serde_json::from_str::<Vec<Value>>(&contents) {
                knowledge_collections.push(serde_json::json!({
                    "collection": collection_name,
                    "chunkCount": chunks.len()
                }));
            }
        }
    }

    Ok(serde_json::json!({
        "manifest": manifest,
        "assistants": assistants,
        "threads": threads,
        "knowledge": knowledge_collections
    }))
}

/// Imports selected items from a .mobius package into the local data store.
///
/// # Arguments
/// * `package_path` - Path to the .mobius file
/// * `assistant_ids` - Which assistants to import
/// * `thread_ids` - Which threads to import
/// * `knowledge_collections` - Which knowledge collections to import
#[command]
pub async fn import_mobius_package<R: Runtime>(
    app_handle: tauri::AppHandle<R>,
    package_path: String,
    assistant_ids: Vec<String>,
    thread_ids: Vec<String>,
    knowledge_collections: Vec<String>,
) -> Result<Value, String> {
    let file = File::open(&package_path)
        .map_err(|e| format!("Failed to open package: {}", e))?;
    let mut archive =
        zip::ZipArchive::new(file).map_err(|e| format!("Invalid .mobius package: {}", e))?;

    let data_folder = get_jan_data_folder_path(app_handle.clone());
    let mut imported_assistants: Vec<Value> = Vec::new();
    let mut imported_threads: Vec<Value> = Vec::new();
    let mut imported_knowledge = 0u32;

    // Import assistants
    let assistants_dir = data_folder.join("assistants");
    if !assistants_dir.exists() {
        let _ = fs::create_dir_all(&assistants_dir);
    }

    for id in &assistant_ids {
        let entry_name = format!("assistants/{}.json", id);
        if let Ok(mut entry) = archive.by_name(&entry_name) {
            let mut contents = String::new();
            entry
                .read_to_string(&mut contents)
                .map_err(|e| format!("Read error: {}", e))?;
            if let Ok(val) = serde_json::from_str::<Value>(&contents) {
                // Write assistant file
                let assistant_path = assistants_dir.join(format!("{}.json", id));
                fs::write(
                    &assistant_path,
                    serde_json::to_string_pretty(&val).unwrap_or_default(),
                )
                .map_err(|e| format!("Write error: {}", e))?;
                imported_assistants.push(val);
            }
        }
    }

    // Import threads (thread.json + messages.jsonl)
    let threads_dir = data_folder.join("threads");
    if !threads_dir.exists() {
        let _ = fs::create_dir_all(&threads_dir);
    }

    for id in &thread_ids {
        let thread_entry_name = format!("threads/{}/thread.json", id);
        let messages_entry_name = format!("threads/{}/messages.jsonl", id);

        // Generate a new thread ID to avoid collisions
        let new_id = uuid::Uuid::new_v4().to_string();
        let thread_dir = threads_dir.join(&new_id);
        if !thread_dir.exists() {
            let _ = fs::create_dir_all(&thread_dir);
        }

        // Import thread metadata
        if let Ok(mut entry) = archive.by_name(&thread_entry_name) {
            let mut contents = String::new();
            entry
                .read_to_string(&mut contents)
                .map_err(|e| format!("Read error: {}", e))?;
            if let Ok(mut val) = serde_json::from_str::<Value>(&contents) {
                // Rewrite the ID to the new one
                val["id"] = serde_json::Value::String(new_id.clone());
                val["object"] = serde_json::Value::String("thread".to_string());
                // Set timestamps
                let now = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs() as i64;
                val["created"] = serde_json::Value::Number(now.into());
                val["updated"] = serde_json::Value::Number(now.into());
                // Ensure assistants array exists
                if val.get("assistants").is_none() {
                    val["assistants"] = serde_json::json!([]);
                }

                let thread_path = thread_dir.join("thread.json");
                fs::write(
                    &thread_path,
                    serde_json::to_string_pretty(&val).unwrap_or_default(),
                )
                .map_err(|e| format!("Write error: {}", e))?;
                imported_threads.push(val);
            }
        }

        // Import messages
        if let Ok(mut entry) = archive.by_name(&messages_entry_name) {
            let mut contents = String::new();
            entry
                .read_to_string(&mut contents)
                .map_err(|e| format!("Read error: {}", e))?;

            // Rewrite thread_id in each message and assign new message IDs
            let mut rewritten = String::new();
            for line in contents.lines() {
                if line.trim().is_empty() {
                    continue;
                }
                if let Ok(mut msg) = serde_json::from_str::<Value>(line) {
                    msg["thread_id"] = serde_json::Value::String(new_id.clone());
                    msg["id"] = serde_json::Value::String(uuid::Uuid::new_v4().to_string());
                    if let Ok(rewritten_line) = serde_json::to_string(&msg) {
                        rewritten.push_str(&rewritten_line);
                        rewritten.push('\n');
                    }
                }
            }

            let messages_path = thread_dir.join("messages.jsonl");
            fs::write(&messages_path, rewritten)
                .map_err(|e| format!("Write error: {}", e))?;
        }
    }

    // Import knowledge chunks — write to a staging area for RAG ingestion
    if !knowledge_collections.is_empty() {
        let knowledge_staging = data_folder.join("knowledge_imports");
        if !knowledge_staging.exists() {
            let _ = fs::create_dir_all(&knowledge_staging);
        }

        for collection in &knowledge_collections {
            let entry_name = format!("knowledge/{}/chunks.json", collection);
            if let Ok(mut entry) = archive.by_name(&entry_name) {
                let mut contents = String::new();
                entry
                    .read_to_string(&mut contents)
                    .map_err(|e| format!("Read error: {}", e))?;

                if let Ok(chunks) = serde_json::from_str::<Vec<Value>>(&contents) {
                    imported_knowledge += chunks.len() as u32;

                    let collection_dir = knowledge_staging.join(collection);
                    if !collection_dir.exists() {
                        let _ = fs::create_dir_all(&collection_dir);
                    }
                    let chunks_path = collection_dir.join("chunks.json");
                    fs::write(
                        &chunks_path,
                        serde_json::to_string_pretty(&chunks).unwrap_or_default(),
                    )
                    .map_err(|e| format!("Write error: {}", e))?;
                }
            }
        }
    }

    Ok(serde_json::json!({
        "importedAssistants": imported_assistants.len(),
        "importedThreads": imported_threads.len(),
        "importedKnowledgeChunks": imported_knowledge,
        "assistants": imported_assistants,
        "threads": imported_threads
    }))
}
