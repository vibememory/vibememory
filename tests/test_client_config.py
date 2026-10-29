import importlib.util
import json
import os
from pathlib import Path

import pytest


@pytest.fixture
def cli(tmp_path, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'skills/vibe-memory/scripts/memory.py'
    spec = importlib.util.spec_from_file_location('client_config_cli', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'config_path', lambda: tmp_path / 'config' / 'client.json')
    monkeypatch.delenv('MEMORY_URL', raising=False)
    monkeypatch.delenv('MEMORY_API_KEY', raising=False)
    return module


def test_configure_verifies_and_hides_secret(cli, monkeypatch, capsys):
    secret = 'private-test-key-should-not-appear'
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    monkeypatch.setattr('sys.stderr.isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda prompt: '')
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt: secret)
    verified = []
    monkeypatch.setattr(cli, 'call', lambda path, **kw: verified.append((path, kw)))
    cli.configure()
    assert verified == [('/v1/me', {'credentials': ('https://vibememory.io', secret)})]
    assert cli.connection() == ('https://vibememory.io', secret)
    if os.name != 'nt':
        assert cli.config_path().stat().st_mode & 0o777 == 0o600
    assert secret not in capsys.readouterr().out
    monkeypatch.setenv('MEMORY_URL', 'https://other.example')
    assert cli.connection() == ('https://other.example', '')
    monkeypatch.setenv('MEMORY_API_KEY', 'explicit-other-key')
    assert cli.connection() == ('https://other.example', 'explicit-other-key')


def test_failed_verification_preserves_saved_credentials(cli, monkeypatch):
    cli.config_path().parent.mkdir()
    cli.config_path().write_text(json.dumps({'url': 'https://vibememory.io', 'api_key': 'original'}))
    cli.config_path().chmod(0o600)
    monkeypatch.setattr('sys.stdin.isatty', lambda: True)
    monkeypatch.setattr('sys.stderr.isatty', lambda: True)
    monkeypatch.setattr('builtins.input', lambda prompt: 'https://other.example')
    monkeypatch.setattr(cli.getpass, 'getpass', lambda prompt: 'rejected-key')

    def reject(*args, **kwargs):
        raise RuntimeError('API returned HTTP 401')

    monkeypatch.setattr(cli, 'call', reject)
    with pytest.raises(RuntimeError, match='401'):
        cli.configure()
    assert cli.read_config()['api_key'] == 'original'
    monkeypatch.setattr('sys.stdin.isatty', lambda: False)
    with pytest.raises(ValueError, match='interactive terminal'):
        cli.configure()


def test_reject_credentials_in_url_and_broad_permissions(cli):
    for url in ['http://remote.example', 'https://user:secret@example.com', 'https://example.com/path']:
        with pytest.raises(ValueError):
            cli.validate_origin(url)
    assert cli.validate_origin('http://127.0.0.1:8080/') == 'http://127.0.0.1:8080'
    if os.name != 'nt':
        cli.config_path().parent.mkdir()
        cli.config_path().write_text('{}')
        cli.config_path().chmod(0o644)
        with pytest.raises(ValueError, match='permissions'):
            cli.read_config()
