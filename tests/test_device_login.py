import sqlite3

import pytest
from conftest import SpyEmbedder
from fastapi.testclient import TestClient

from vibe_memory.app import create_app

ORIGIN = 'https://vibememory.io'


@pytest.fixture
def web(settings):
    settings = settings.model_copy(update={'public_origin': ORIGIN, 'api_keys': {}})
    with TestClient(create_app(settings, SpyEmbedder()), base_url=ORIGIN) as client:
        client.headers['Origin'] = ORIGIN
        yield client, settings


def signup(client):
    assert client.post('/auth/signup', json={
        'email': 'device@example.invalid', 'password': 'test-device-password-123', 'name': 'Device QA'
    }).status_code == 200


def allow_poll(settings):
    with sqlite3.connect(settings.data_dir / 'auth.sqlite') as db:
        db.execute('UPDATE device_logins SET polled_at=0')


def test_web_approval_one_time_key_and_no_secret_in_browser(web):
    client, settings = web
    pending = client.post('/auth/device/start', json={
        'name': 'Claude Code', 'vault_access': True
    }).json()
    assert pending['verification_uri_complete'] == ORIGIN+'/connect?code='+pending['user_code']
    assert pending['device_code'] not in pending['verification_uri_complete']
    assert client.get('/auth/device', params={'code': pending['user_code']}).status_code == 401
    assert client.post('/auth/device/approve', json={
        'user_code': pending['user_code'], 'approved': True
    }).status_code == 401
    assert client.post('/auth/device/poll', json={'device_code': pending['device_code']}).json() == {'state': 'pending'}
    assert client.post('/auth/device/poll', json={'device_code': pending['device_code']}).status_code == 429
    signup(client)
    device = client.get('/auth/device', params={'code': pending['user_code']}).json()
    assert device['name'] == 'Claude Code' and device['vault_access'] is True
    approval = {'user_code': pending['user_code'], 'approved': True}
    assert client.post('/auth/device/approve', json=approval, headers={'Origin': 'https://evil.example'}).status_code == 403
    response = client.post('/auth/device/approve', json=approval)
    assert response.json() == {'state': 'approved'}
    assert client.post('/auth/device/approve', json=approval).status_code == 410
    allow_poll(settings)
    result = client.post('/auth/device/poll', json={'device_code': pending['device_code']}).json()
    assert result['state'] == 'connected'
    me = client.get('/v1/me', headers={'Authorization': 'Bearer '+result['key']})
    assert me.status_code == 200 and me.json()['vault_access'] is True
    assert client.post('/auth/device/poll', json={'device_code': pending['device_code']}).status_code == 410
    keys = client.get('/auth/api-keys').json()['items']
    assert len(keys) == 1 and keys[0]['name'] == 'Claude Code'
    assert keys[0]['vault_access'] is True
    assert result['key'] not in str(keys)
    with sqlite3.connect(settings.data_dir / 'auth.sqlite') as db:
        dump = '\n'.join(db.iterdump())
    assert result['key'] not in dump and pending['device_code'] not in dump


def test_denied_expired_and_invalid_requests(web):
    client, settings = web
    signup(client)
    for denied in (True, False):
        pending = client.post('/auth/device/start', json={'name': 'Codex'}).json()
        if denied:
            assert client.post('/auth/device/approve', json={
                'user_code': pending['user_code'], 'approved': False
            }).json() == {'state': 'denied'}
        else:
            with sqlite3.connect(settings.data_dir / 'auth.sqlite') as db:
                db.execute('UPDATE device_logins SET expires_at=0')
        response = client.post('/auth/device/poll', json={'device_code': pending['device_code']})
        assert response.status_code == (403 if denied else 410)
    assert client.post('/auth/device/poll', json={'device_code': 'unknown'*8}).status_code == 410
    assert client.get('/auth/device?code=invalid').status_code == 422
