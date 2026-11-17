"""T005 synthetic offline RED contracts for the stdlib transport boundary."""

from __future__ import annotations

import ast
import io
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request

import pytest
from embed_fixtures import (
    FAKE_KEY,
    FakeHttpResponse,
    FakeOpenUrl,
    assert_sanitized,
    json_bytes,
    response_body,
)

from sciscope.embedding.config import (
    DEFAULT_BASE_URL,
    EmbeddingConfigError,
)
from sciscope.embedding.openai_client import (
    OpenAIConnection,
    TransportConnectionError,
    TransportRequest,
    TransportTimeout,
    UrllibTransport,
    embeddings_url,
    read_api_key,
    read_base_url,
)


def connection() -> OpenAIConnection:
    """Build a connection containing only an obviously fake credential."""
    return OpenAIConnection(FAKE_KEY, "https://example.invalid/v1/embeddings")


def request() -> TransportRequest:
    """Build synthetic payload and timeout with no URL or credential fields."""
    return TransportRequest({"input": ["Synthetic é."], "dimensions": 2}, 5.0)


@pytest.mark.parametrize(
    ("base", "expected"),
    [
        ("https://api.openai.com", "https://api.openai.com/v1/embeddings"),
        ("https://example.invalid/v1", "https://example.invalid/v1/embeddings"),
        (
            "https://example.invalid/v1/",
            "https://example.invalid/v1/embeddings",
        ),
        (
            "https://example.invalid/root/",
            "https://example.invalid/root/v1/embeddings",
        ),
    ],
)
def test_embeddings_url_composition(base: str, expected: str) -> None:
    """T005-H01: append exactly one endpoint suffix to the configured base."""
    assert embeddings_url(base) == expected


def test_exact_headers_body_and_bounded_response() -> None:
    """T005-H02: serialize ASCII JSON and send only the required headers."""
    body = response_body()
    http = FakeHttpResponse(
        json_bytes(body),
        headers={
            "X-RateLimit-Remaining-Tokens": "9",
            "Retry-After": "2",
            "Set-Cookie": FAKE_KEY,
            "x-ratelimit-control": "bad\rvalue",
            "x-ratelimit-long": "x" * 65,
            "x-ratelimit-unicode": "é",
        },
    )
    opener = FakeOpenUrl(http)
    result = UrllibTransport(connection(), open_url=opener).post_json(request())
    sent, timeout = opener.calls[0]
    assert sent.full_url == "https://example.invalid/v1/embeddings"
    assert sent.get_method() == "POST"
    assert dict(
        (name.lower(), value) for name, value in sent.header_items()
    ) == {
        "authorization": "Bearer " + FAKE_KEY,
        "content-type": "application/json",
        "accept": "application/json",
        "user-agent": "sciscope-embed/0",
    }
    assert sent.data == json_bytes(request().payload)
    assert b"\\u00e9" in sent.data
    assert timeout == 5.0
    assert result.status == 200 and result.body == body
    assert dict(result.headers) == {
        "x-ratelimit-remaining-tokens": "9",
        "retry-after": "2",
    }
    assert http.read_sizes and all(
        0 < size <= 16 * 1024 * 1024 + 1 for size in http.read_sizes
    )


@pytest.mark.parametrize("status", [400, 401, 403, 404, 429, 500, 503])
@pytest.mark.parametrize("valid_json", [False, True])
def test_http_errors_parse_only_safe_error_discriminators(
    status: int, valid_json: bool, capsys: pytest.CaptureFixture[str]
) -> None:
    """T005-H03: bounded HTTP errors expose classification without raw prose."""
    raw = json_bytes(
        {
            "error": {
                "code": "insufficient_quota",
                "type": "quota",
                "message": FAKE_KEY,
            }
        }
    )
    if not valid_json:
        raw = ("not JSON " + FAKE_KEY).encode()
    error = HTTPError(
        connection().url,
        status,
        FAKE_KEY,
        {"Retry-After": "2"},
        io.BytesIO(raw),
    )
    opener = FakeOpenUrl(error)
    result = UrllibTransport(connection(), open_url=opener).post_json(request())
    assert result.status == status
    assert result.body == (
        {"error": {"code": "insufficient_quota", "type": "quota"}}
        if valid_json
        else None
    )
    assert FAKE_KEY not in repr(result)
    assert len(opener.calls) == 1
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_default_opener_refuses_redirects_without_forwarding_authorization(
    monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """T005-H04: default opener blocks redirects before a second request."""
    captured_handlers: list[object] = []
    requests: list[Request] = []

    class InspectOpener:
        """Exercise the installed redirect handler entirely in memory."""

        def open(self, sent: Request, *, timeout: float) -> FakeHttpResponse:
            """Invoke redirect handling without opening either URL."""
            requests.append(sent)
            handler = next(
                h
                for h in captured_handlers
                if isinstance(h, HTTPRedirectHandler)
            )
            try:
                redirected = handler.redirect_request(
                    sent,
                    io.BytesIO(),
                    status,
                    "redirect",
                    {},
                    "https://other.invalid/steal",
                )
            except HTTPError:
                redirected = None
            assert redirected is None
            raise HTTPError(sent.full_url, status, "redirect", {}, io.BytesIO())

    def build(*handlers: object) -> InspectOpener:
        captured_handlers.extend(handlers)
        return InspectOpener()

    monkeypatch.setattr("urllib.request.build_opener", build)
    result = UrllibTransport(connection()).post_json(request())
    assert result.status == status
    assert len(requests) == 1
    assert requests[0].get_header("Authorization") == "Bearer " + FAKE_KEY


@pytest.mark.parametrize(
    ("failure", "expected"),
    [
        (TimeoutError(FAKE_KEY), TransportTimeout),
        (URLError(TimeoutError(FAKE_KEY)), TransportTimeout),
        (URLError(FAKE_KEY), TransportConnectionError),
        (OSError(FAKE_KEY), TransportConnectionError),
        (ConnectionError(FAKE_KEY), TransportConnectionError),
        (ValueError(FAKE_KEY), TransportConnectionError),
        (RuntimeError(FAKE_KEY), TransportConnectionError),
    ],
)
def test_transport_failures_have_no_secret_or_exception_chain(
    failure: Exception,
    expected: type[Exception],
    capsys: pytest.CaptureFixture[str],
) -> None:
    """T005-H05: sanitize every opener failure, including header errors."""
    with pytest.raises(expected) as caught:
        UrllibTransport(connection(), open_url=FakeOpenUrl(failure)).post_json(
            request()
        )
    assert str(caught.value) == ""
    assert_sanitized(caught.value)
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "raw",
    [b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b"not JSON", b"\xff"],
)
def test_invalid_json_response_is_none(raw: bytes) -> None:
    """T005-H06: reject nonstandard constants and invalid response encoding."""
    result = UrllibTransport(
        connection(), open_url=FakeOpenUrl(FakeHttpResponse(raw))
    ).post_json(request())
    assert result.body is None


@pytest.mark.parametrize("http_error", [False, True])
def test_oversized_body_is_bounded_and_not_parsed(http_error: bool) -> None:
    """T005-H07: bound successful and HTTPError body reads before parsing."""
    http = FakeHttpResponse(b" " * 32 + b"{}")
    outcome = (
        HTTPError(connection().url, 429, "large", {}, http)
        if http_error
        else http
    )
    result = UrllibTransport(
        connection(), open_url=FakeOpenUrl(outcome), max_response_bytes=8
    ).post_json(request())
    assert result.body is None
    assert http.read_sizes and all(0 < size <= 9 for size in http.read_sizes)


@pytest.mark.parametrize(
    "base",
    [
        "http://example.invalid",
        "https://",
        "//example.invalid",
        "https://user:secret@example.invalid",
        "https://example.invalid?q=1",
        "https://example.invalid#fragment",
        "",
    ],
)
def test_rejects_unsafe_base_url(base: str) -> None:
    """T005-H08: accept only HTTPS hosts without credentials or suffix data."""
    with pytest.raises(EmbeddingConfigError) as caught:
        read_base_url({"OPENAI_BASE_URL": base})
    assert caught.value.code == "invalid-base-url"
    assert base not in str(caught.value) if base else True
    assert_sanitized(caught.value)


@pytest.mark.parametrize(
    ("env", "base", "custom"),
    [
        ({}, DEFAULT_BASE_URL, False),
        ({"OPENAI_BASE_URL": DEFAULT_BASE_URL + "/"}, DEFAULT_BASE_URL, False),
        (
            {"OPENAI_BASE_URL": "https://example.invalid/root/"},
            "https://example.invalid/root",
            True,
        ),
    ],
)
def test_base_url_normalization_and_custom_flag(
    env: dict[str, str], base: str, custom: bool
) -> None:
    """T005-H09: retain only a normalized base and explicit custom flag."""
    assert read_base_url(env) == (base, custom)
    value = OpenAIConnection(FAKE_KEY, embeddings_url(base), custom)
    assert FAKE_KEY not in repr(value)
    assert base not in repr(value)


@pytest.mark.parametrize(
    "bad",
    [
        "",
        " \t",
        "fake key",
        "fake\tkey",
        "fake\rkey",
        "fake\nkey",
        "fake\x00key",
        "fake\x7fkey",
        "fakeékey",
    ],
)
def test_key_validation_precedes_transport(bad: str) -> None:
    """T005-H10: reject unsafe header characters before constructing HTTP."""
    with pytest.raises(EmbeddingConfigError) as caught:
        read_api_key({"OPENAI_API_KEY": bad})
    assert caught.value.code == (
        "missing-api-key" if not bad.strip() else "invalid-api-key"
    )
    assert_sanitized(caught.value)


def test_embedding_modules_never_import_logging() -> None:
    """T005-H11: prohibit logging imports throughout the embedding package."""
    directory = Path(__file__).resolve().parents[2] / "src/sciscope/embedding"
    modules = list(directory.glob("*.py"))
    assert modules
    for module in modules:
        for node in ast.walk(ast.parse(module.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                assert all(
                    alias.name.split(".")[0] != "logging"
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                assert (node.module or "").split(".")[0] != "logging"
