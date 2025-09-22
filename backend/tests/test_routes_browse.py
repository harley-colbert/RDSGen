from __future__ import annotations

import pytest

from app.routes import browse


class DummyFuture:
    def __init__(self, result, should_raise=False):
        self._result = result
        self._should_raise = should_raise

    def result(self):
        if self._should_raise:
            raise RuntimeError("dialog failed")
        return self._result


class DummyExecutor:
    def __init__(self, result, should_raise=False):
        self._result = result
        self._should_raise = should_raise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401
        return False

    def submit(self, func, *args):  # noqa: ANN001
        return DummyFuture(self._result, self._should_raise)


@pytest.fixture()
def _patch_executor(monkeypatch, request):
    result, should_raise = request.param

    def factory(*args, **kwargs):  # noqa: ANN001
        return DummyExecutor(result, should_raise)

    monkeypatch.setattr(browse, "ProcessPoolExecutor", factory)


@pytest.mark.parametrize("_patch_executor", [("C:/tmp/file.txt", False)], indirect=True)
def test_browse_success(client):
    resp = client.get("/api/browse?mode=open_file")
    assert resp.status_code == 200
    assert resp.get_json()["path"] == "C:/tmp/file.txt"


@pytest.mark.parametrize("_patch_executor", [("", True)], indirect=True)
def test_browse_error(client):
    resp = client.get("/api/browse")
    assert resp.status_code == 500
    assert resp.get_json()["ok"] is False
