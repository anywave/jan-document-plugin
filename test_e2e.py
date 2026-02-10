#!/usr/bin/env python3
"""
End-to-end test suite for Jan Document Plugin.

Tests all major functionality:
- Health check
- Document upload (TXT)
- Document listing
- Semantic search / query
- Chat completions (non-streaming)
- Chat completions (streaming)
- Models list
- Document deletion

Usage:
    python test_e2e.py [--base-url http://localhost:1338]
"""

import httpx
import json
import tempfile
import os
import sys

BASE = sys.argv[2] if len(sys.argv) > 2 and sys.argv[1] == '--base-url' else 'http://localhost:1338'

passed = 0
failed = 0


def test(name, condition, detail=''):
    global passed, failed
    if condition:
        passed += 1
        print(f'  [PASS] {name}')
    else:
        failed += 1
        print(f'  [FAIL] {name}: {detail}')


def main():
    global passed, failed

    print('=' * 60)
    print('Jan Document Plugin - End-to-End Test Suite')
    print(f'Target: {BASE}')
    print('=' * 60)

    # === Health Check ===
    print('\n--- Health Check ---')
    try:
        r = httpx.get(f'{BASE}/health', timeout=10)
        test('Health endpoint responds', r.status_code == 200)
        data = r.json()
        test('Status is healthy', data['status'] == 'healthy')
        test('Jan connected', data['jan_connected'] is True)
    except httpx.ConnectError:
        print('  [FAIL] Cannot connect to server. Is it running?')
        sys.exit(1)

    # === Document Upload (TXT) ===
    print('\n--- Document Upload ---')
    test_path = os.path.join(tempfile.gettempdir(), 'e2e_test.txt')
    with open(test_path, 'w') as f:
        f.write(
            'Quantum computing uses qubits instead of classical bits. '
            'Unlike classical bits which are either 0 or 1, qubits can exist in superposition. '
            'This allows quantum computers to solve certain problems exponentially faster '
            'than classical computers. IBM and Google are leading companies in quantum '
            'computing research.'
        )

    with open(test_path, 'rb') as f:
        r = httpx.post(
            f'{BASE}/documents',
            files={'file': ('quantum_computing.txt', f, 'text/plain')},
            timeout=60,
        )
    test('Upload returns 200', r.status_code == 200)
    upload_data = r.json()
    test('Upload success flag', upload_data['success'] is True)
    test('Has doc_hash', len(upload_data['doc_hash']) > 0)
    test('Has chunks', upload_data['chunks'] > 0)
    doc_hash = upload_data['doc_hash']
    os.unlink(test_path)

    # === Document List ===
    print('\n--- Document List ---')
    r = httpx.get(f'{BASE}/documents', timeout=10)
    test('List returns 200', r.status_code == 200)
    docs = r.json()
    test('Document count > 0', docs['total'] > 0)
    test('Our doc is listed', any(d['doc_hash'] == doc_hash for d in docs['documents']))

    # === Semantic Search ===
    print('\n--- Semantic Search ---')
    r = httpx.post(
        f'{BASE}/documents/query',
        data={'query': 'What is a qubit?', 'n_results': 3},
        timeout=30,
    )
    test('Query returns 200', r.status_code == 200)
    query_data = r.json()
    test('Has context in result', len(query_data.get('context', '')) > 0)
    test('Context mentions quantum', 'quantum' in query_data.get('context', '').lower())

    # === Chat Completions (non-streaming) ===
    print('\n--- Chat Completions (non-streaming) ---')
    payload = {
        'model': 'qwen2.5:7b-instruct',
        'messages': [
            {'role': 'user', 'content': 'What is a qubit and how does it differ from a classical bit?'}
        ],
        'temperature': 0.3,
        'max_tokens': 150,
        'stream': False,
    }
    r = httpx.post(f'{BASE}/v1/chat/completions', json=payload, timeout=120)
    test('Chat returns 200', r.status_code == 200)
    chat_data = r.json()
    test('Has choices', len(chat_data.get('choices', [])) > 0)
    answer = chat_data['choices'][0]['message']['content']
    test(
        'Answer mentions qubit/quantum',
        'qubit' in answer.lower() or 'quantum' in answer.lower(),
    )
    test('Has usage info', 'usage' in chat_data)

    # === Chat Completions (streaming) ===
    print('\n--- Chat Completions (streaming) ---')
    payload['stream'] = True
    payload['messages'] = [
        {'role': 'user', 'content': 'Which companies research quantum computing?'}
    ]
    chunks_received = 0
    stream_content = ''
    try:
        with httpx.stream(
            'POST', f'{BASE}/v1/chat/completions', json=payload, timeout=120
        ) as r:
            test('Stream returns 200', r.status_code == 200)
            for line in r.iter_lines():
                if line.startswith('data: ') and line != 'data: [DONE]':
                    chunk = json.loads(line[6:])
                    delta = chunk.get('choices', [{}])[0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        stream_content += content
                        chunks_received += 1
        test('Received stream chunks', chunks_received > 0)
        test(
            'Stream mentions IBM or Google',
            'ibm' in stream_content.lower() or 'google' in stream_content.lower(),
        )
    except Exception as e:
        test('Streaming works', False, str(e))

    # === Models List ===
    print('\n--- Models List ---')
    r = httpx.get(f'{BASE}/v1/models', timeout=10)
    test('Models returns 200', r.status_code == 200)

    # === Document Deletion ===
    print('\n--- Document Deletion ---')
    r = httpx.delete(f'{BASE}/documents/{doc_hash}', timeout=30)
    test('Delete returns 200', r.status_code == 200)
    del_data = r.json()
    test('Delete success', del_data.get('success') is True)

    # Verify removal
    r = httpx.get(f'{BASE}/documents', timeout=10)
    remaining = r.json()
    test(
        'Document removed from list',
        not any(d['doc_hash'] == doc_hash for d in remaining['documents']),
    )

    # === Summary ===
    print('\n' + '=' * 60)
    total = passed + failed
    print(f'Results: {passed}/{total} passed, {failed} failed')
    if failed == 0:
        print('ALL TESTS PASSED')
    else:
        print(f'FAILURES: {failed}')
    print('=' * 60)
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
