import json

import pytest
from conftest import KEY_A, KEY_A2, KEY_B, SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app


def decode(response):
    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/event-stream')
    assert response.headers['cache-control'] == 'no-store'
    events = []
    for block in response.text.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in block.splitlines() if ': ' in line)
        if 'data' in fields:
            events.append(dict(id=int(fields['id']), event=fields['event'],
                               data=json.loads(fields['data'])))
    return events


def test_events_owner_replay_updates_and_failed_writes(client, embedder):
    record = client.post('/v1/memories', json={'content': 'private text', 'keywords': ['tea']}).json()
    other = client.post('/v1/entities', json={
        'name': 'tea', 'entity_type': 'drink', 'description': '', 'keywords': ['tea']
    }).json()
    relation = client.post('/v1/relations', json={
        'source_id': record['id'], 'target_id': other['id'],
        'relation': 'LIKES', 'reason': 'explicit'
    }).json()
    assert client.put('/v1/records/'+record['id']+'/keywords', json={'keywords': ['green tea']}).status_code == 200
    assert client.patch('/v1/relations/'+relation['id'], json={
        'status': 'retracted', 'reason': 'corrected', 'expected_version': 99
    }).status_code == 409
    assert client.patch('/v1/relations/'+relation['id'], json={
        'status': 'retracted', 'reason': 'corrected', 'expected_version': 1
    }).status_code == 200
    calls = len(embedder.calls)
    response = client.get('/v1/events?seconds=1', headers={'Authorization': 'Bearer '+KEY_A2})
    assert 'private text' not in response.text
    events = decode(response)
    assert [e['event'] for e in events] == [
        'memory.created', 'entity.created', 'relation.created', 'memory.updated', 'relation.updated'
    ]
    assert len(embedder.calls) == calls
    assert decode(client.get('/v1/events?seconds=1', headers={'Authorization': 'Bearer '+KEY_B})) == []
    assert client.delete('/v1/records/'+record['id']).status_code == 204
    tail = decode(client.get('/v1/events?seconds=1', headers={'Last-Event-ID': str(events[-1]['id'])}))
    assert [e['event'] for e in tail] == ['memory.deleted']
    assert tail[0]['data']['incident_relations_removed'] is True
    assert client.get('/v1/events', headers={'Last-Event-ID': 'invalid'}).status_code == 422
    assert client.get('/v1/events', headers={'Authorization': 'Bearer bad'}).status_code == 401


def test_transaction_rollback_and_restart(settings):
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        db = client.app.state.store
        with pytest.raises(RuntimeError), db.transaction():
            db._event('alice', 'memory.created', {'record_id': 'rolled-back'})
            raise RuntimeError('rollback')
        assert db.events('alice') == []
        response = client.post('/v1/memories', json={'content': 'persisted', 'keywords': ['tea']},
                               headers={'Authorization': 'Bearer '+KEY_A})
        assert response.status_code == 201
        event = db.events('alice')[0]
    with TestClient(create_app(settings, SpyEmbedder())) as client:
        assert client.app.state.store.events('alice') == [event]
        assert decode(client.get('/v1/events?seconds=1', headers={
            'Authorization': 'Bearer '+KEY_A, 'Last-Event-ID': str(event['id'])
        })) == []


def test_listener_receives_live_write_and_resumes(settings, tmp_path, monkeypatch, capsys):
    import importlib.util
    import socket
    import threading
    import time
    from pathlib import Path

    import httpx
    import uvicorn

    spec = importlib.util.spec_from_file_location(
        'event_helper', Path(__file__).resolve().parents[1] / 'skills/vibe-memory/scripts/memory.py'
    )
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    base = f'http://127.0.0.1:{sock.getsockname()[1]}'
    server = uvicorn.Server(uvicorn.Config(create_app(settings, SpyEmbedder()), log_level='error'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [sock]}, daemon=True)
    thread.start()
    monkeypatch.setenv('MEMORY_URL', base)
    monkeypatch.setenv('MEMORY_API_KEY', KEY_A)
    cursor = tmp_path / 'agent.cursor'
    errors = []

    def watch():
        try:
            helper.watch_events(seconds=2, cursor_file=cursor)
        except Exception as error:
            errors.append(error)

    try:
        deadline = time.monotonic() + 10
        while not server.started and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        listener = threading.Thread(target=watch)
        listener.start()
        time.sleep(0.2)
        with httpx.Client(base_url=base, headers={'Authorization': 'Bearer '+KEY_A}) as client:
            saved = client.post('/v1/memories', json={'content': 'live', 'keywords': ['tea']})
            assert saved.status_code == 201
        listener.join(timeout=10)
        assert not listener.is_alive()
        assert not errors
        lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
        assert len(lines) == 1
        assert lines[0]['data']['record_id'] == saved.json()['id']
        assert int(cursor.read_text()) == lines[0]['id']
        helper.watch_events(seconds=1, cursor_file=cursor)
        assert capsys.readouterr().out == ''
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
