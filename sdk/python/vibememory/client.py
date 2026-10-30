"""Tiny dependency-free Vibe Memory client; it performs no LLM calls."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request


class VibeMemoryError(RuntimeError):
    def __init__(self, status, body):
        super().__init__(f"Vibe Memory {status}: {body}")
        self.status, self.body = status, body


class VibeMemoryClient:
    def __init__(self, base_url, token, namespace="default", timeout=20):
        self.base_url, self.token, self.namespace, self.timeout = base_url.rstrip("/"), token, namespace, timeout

    def _request(self, path, method="GET", payload=None, retry=False):
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(self.base_url + path, data=body, method=method, headers={
            "Authorization": "Bearer " + self.token,
            "Content-Type": "application/json",
            "X-Vibe-Memory-Namespace": self.namespace,
        })
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return None if response.status == 204 else json.load(response)
        except urllib.error.HTTPError as error:
            if error.code == 429 and retry:
                time.sleep(min(int(error.headers.get("Retry-After", "1")), 30))
                return self._request(path, method, payload, False)
            raise VibeMemoryError(error.code, error.read().decode(errors="replace")) from None

    def get(self, record_id):
        return self._request("/v1/records/" + urllib.parse.quote(record_id, safe=""))

    def search(self, keywords, match_mode="hybrid"):
        return self._request("/v1/search", "POST", {"keywords": keywords, "match_mode": match_mode}, True)

    def create(self, content, keywords, client_request_id=None):
        payload = {"content": content, "keywords": keywords, "kind": "fact"}
        if client_request_id:
            payload["client_request_id"] = client_request_id
        return self._request("/v1/memories", "POST", payload, bool(client_request_id))

    def correct(self, previous_id, expected_previous_version, replacement, reason, client_request_id):
        return self._request("/v1/corrections/memories", "POST", {
            "previous_id": previous_id, "expected_previous_version": expected_previous_version,
            "replacement": {**replacement, "kind": replacement.get("kind", "fact")},
            "relation": "CORRECTS", "correction_scope": "full", "reason": reason,
            "client_request_id": client_request_id,
        }, True)

    def list(self, limit=50, offset=0):
        return self._request(f"/v1/records?limit={limit}&offset={offset}")

    def create_entities(self, items):
        return self._request("/v1/entities/batch", "POST", {"items": items, "return": "minimal", "atomic": False})

    def context_bundle(self, **selectors):
        return self._request("/v1/context-bundle", "POST", selectors, True)
