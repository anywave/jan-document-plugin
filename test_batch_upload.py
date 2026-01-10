#!/usr/bin/env python3
"""
Test script for batch upload and resource monitoring.

Run this after starting the plugin to verify batch processing works.

Usage:
    python test_batch_upload.py [directory_with_documents]
    
Example:
    python test_batch_upload.py C:\Users\YourName\Documents\TestDocs
"""

import os
import sys
import json
import requests
from pathlib import Path
from typing import List

BASE_URL = "http://localhost:1338"


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_json(data: dict, indent: int = 2):
    """Pretty print JSON data."""
    print(json.dumps(data, indent=indent))


def check_health():
    """Check plugin health and resource status."""
    print_header("1. HEALTH CHECK")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        data = response.json()
        
        print(f"Status: {data['status']}")
        print(f"Jan Connected: {data['jan_connected']}")
        print(f"Documents Indexed: {data['documents_indexed']}")
        
        if 'system_resources' in data:
            print(f"\nSystem Resources:")
            for key, value in data['system_resources'].items():
                print(f"  {key}: {value}")
        
        return data['status'] == 'healthy'
        
    except Exception as e:
        print(f"ERROR: Could not connect to plugin: {e}")
        print(f"Make sure the plugin is running at {BASE_URL}")
        return False


def check_capacity():
    """Check current load capacity."""
    print_header("2. LOAD CAPACITY")
    
    try:
        response = requests.get(f"{BASE_URL}/documents/capacity", timeout=10)
        data = response.json()
        
        print(f"CPU Usage: {data['cpu_percent']}%")
        print(f"Memory Usage: {data['memory_percent']}%")
        print(f"Memory Available: {data['memory_available_mb']:.0f} MB")
        print(f"\nRecommendations:")
        print(f"  Processing Mode: {data['recommended_mode']}")
        print(f"  Max Concurrent Files: {data['max_concurrent_files']}")
        print(f"  Recommended Workers: {data['recommended_workers']}")
        
        if data['warnings']:
            print(f"\nWarnings:")
            for w in data['warnings']:
                print(f"  ⚠️  {w}")
        
        return data
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def find_test_files(directory: str) -> List[Path]:
    """Find supported document files in directory."""
    supported = {'.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md', '.csv',
                 '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.gif', '.webp'}
    
    files = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"Directory not found: {directory}")
        return files
    
    for file in dir_path.iterdir():
        if file.is_file() and file.suffix.lower() in supported:
            files.append(file)
    
    return files


def upload_single_file(file_path: Path):
    """Upload a single file."""
    print(f"\nUploading: {file_path.name}")
    
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f)}
            response = requests.post(
                f"{BASE_URL}/documents",
                files=files,
                timeout=120
            )
        
        data = response.json()
        
        if data.get('success'):
            print(f"  ✓ Success: {data['chunks']} chunks, ~{data['tokens_estimate']} tokens")
        else:
            print(f"  ✗ Failed: {data.get('error', 'Unknown error')}")
        
        return data
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return None


def upload_batch(file_paths: List[Path]):
    """Upload multiple files as a batch."""
    print_header("4. BATCH UPLOAD")
    
    print(f"Uploading {len(file_paths)} files...")
    for f in file_paths:
        size_kb = f.stat().st_size / 1024
        print(f"  - {f.name} ({size_kb:.1f} KB)")
    
    try:
        files = []
        file_handles = []
        
        for path in file_paths:
            fh = open(path, 'rb')
            file_handles.append(fh)
            files.append(('files', (path.name, fh)))
        
        print("\nProcessing...")
        response = requests.post(
            f"{BASE_URL}/documents/batch",
            files=files,
            timeout=300  # 5 minute timeout for large batches
        )
        
        # Close all file handles
        for fh in file_handles:
            fh.close()
        
        data = response.json()
        
        print(f"\n{'─'*40}")
        print(f"BATCH RESULTS")
        print(f"{'─'*40}")
        print(f"Batch ID: {data['batch_id']}")
        print(f"Processing Mode: {data['processing_mode']}")
        print(f"Workers Used: {data['worker_count']}")
        print(f"\nFiles: {data['completed_files']}/{data['total_files']} completed")
        if data['failed_files'] > 0:
            print(f"       {data['failed_files']} failed")
        print(f"Total Chunks: {data['total_chunks']}")
        
        if data['warnings']:
            print(f"\nWarnings:")
            for w in data['warnings']:
                print(f"  ⚠️  {w}")
        
        print(f"\nPer-File Status:")
        for f in data['files']:
            status_icon = "✓" if f['status'] == 'completed' else "✗"
            duration = f.get('duration_seconds')
            duration_str = f" ({duration:.1f}s)" if duration else ""
            print(f"  {status_icon} {f['filename']}: {f['chunks_created']} chunks{duration_str}")
            if f.get('error_message'):
                print(f"      Error: {f['error_message']}")
        
        return data
        
    except Exception as e:
        print(f"ERROR: {e}")
        return None


def list_indexed_documents():
    """List all indexed documents."""
    print_header("5. INDEXED DOCUMENTS")
    
    try:
        response = requests.get(f"{BASE_URL}/documents", timeout=10)
        data = response.json()
        
        if not data['documents']:
            print("No documents indexed yet.")
            return
        
        print(f"Total: {len(data['documents'])} documents\n")
        
        for doc in data['documents']:
            print(f"  📄 {doc['filename']}")
            print(f"     Hash: {doc['doc_hash'][:12]}...")
            print(f"     Chunks: {doc['chunks']}")
            print(f"     Indexed: {doc['indexed_at']}")
            print()
        
    except Exception as e:
        print(f"ERROR: {e}")


def test_query(query: str):
    """Test document retrieval with a query."""
    print_header("6. TEST QUERY")
    
    print(f"Query: \"{query}\"\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/documents/query",
            json={"query": query, "top_k": 3},
            timeout=30
        )
        
        data = response.json()
        
        print(f"Found {len(data['results'])} relevant chunks:\n")
        
        for i, result in enumerate(data['results'], 1):
            print(f"Result {i} (relevance: {result['relevance']:.2f})")
            print(f"  Source: {result['source']}")
            print(f"  Preview: {result['content'][:200]}...")
            print()
        
    except Exception as e:
        print(f"ERROR: {e}")


def main():
    """Main test flow."""
    print("\n" + "="*60)
    print("  JAN DOCUMENT PLUGIN - BATCH UPLOAD TEST")
    print("="*60)
    
    # 1. Health check
    if not check_health():
        print("\n❌ Plugin not healthy. Please start JanDocumentPlugin.bat first.")
        sys.exit(1)
    
    # 2. Check capacity
    capacity = check_capacity()
    
    # 3. Find test files
    if len(sys.argv) > 1:
        test_dir = sys.argv[1]
    else:
        # Default to current directory
        test_dir = os.getcwd()
    
    print_header("3. FINDING TEST FILES")
    print(f"Looking in: {test_dir}")
    
    files = find_test_files(test_dir)
    
    if not files:
        print(f"\nNo supported documents found in {test_dir}")
        print("Supported formats: PDF, DOCX, XLSX, TXT, images")
        print("\nTo test batch upload, run:")
        print(f"  python {sys.argv[0]} <path_to_documents>")
        return
    
    print(f"Found {len(files)} files:")
    for f in files[:10]:  # Show first 10
        print(f"  - {f.name}")
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more")
    
    # 4. Batch upload
    # Limit to recommended capacity
    max_files = capacity['max_concurrent_files'] if capacity else 5
    batch_files = files[:min(len(files), max_files)]
    
    if len(files) > max_files:
        print(f"\n⚠️  Limiting to {max_files} files based on current capacity")
    
    result = upload_batch(batch_files)
    
    if result and result['completed_files'] > 0:
        # 5. List indexed
        list_indexed_documents()
        
        # 6. Test query
        test_query("What is the main topic of these documents?")
    
    print_header("TEST COMPLETE")
    print("✓ Batch upload functionality verified")
    print(f"✓ Processing mode used: {result['processing_mode'] if result else 'N/A'}")


if __name__ == "__main__":
    main()
