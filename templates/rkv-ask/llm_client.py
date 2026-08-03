"""Ask AI provider layer — reference implementation. See PATTERNS.md §1.

Copy into the project (e.g. `src/core/llm_client.py` or
`src/features/ask_ai/providers.py`), rename `<PROJECT>` in the docstrings
below to the real project name, and prune providers to what the project
actually needs. Everything in this file exists because a specific mistake
already cost real debugging time on a real project — see the inline notes
before "fixing" one of these away.

**Do not add a plain metered-API-key Anthropic provider back in without a
live test.** ANTHROPIC_API_KEY on this machine (kashivis@gmail.com) is valid
and correctly formed but has a **zero credit balance** — `POST /api/ask/test`
returns "Your credit balance is too low to access the Anthropic API." This
was discovered independently on two projects (kite, then ibf) because the
second build re-added the provider from memory instead of copying this file.
Claude is reached through `CLAUDE_CODE_OAUTH_TOKEN` instead (billed against
the Claude Code subscription, not metered API usage) — `ClaudeOAuthClient`
below. If a future key genuinely has a balance, prove it with
`POST /api/ask/test` before shipping the provider as selectable; a provider
that fails its own live test must be deleted from the registry, not merely
left in place with a disabled button — "configured" and "actually works" are
different claims (see the two-endpoint rule, PATTERNS.md §1a) and only
removal prevents someone re-discovering the failure by hand a third time.

**The Gemini SDK is `google-genai` (`from google import genai`), not the
older `google-generativeai` package.** They are different PyPI distributions
with different import paths; the old one is deprecated but still turns up in
older tutorials and training data. `pyproject.toml`'s `ai` extra must pin
`google-genai>=1.0`.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Transient provider errors only. Auth failures and exhausted daily quotas are
# propagated immediately — retrying those just burns time and hides the cause.
_RETRY_BACKOFF = (2.0, 5.0)
_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})
_TRANSIENT_TOKENS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "overloaded")

DEFAULT_PROVIDER = "gemini"


class LLMUnavailable(RuntimeError):
    """The selected provider is not configured or could not be reached."""


@dataclass(frozen=True)
class Answer:
    """What a provider returned, plus how it got there.

    `web_used` is the *observed* outcome, not the request: asking for web
    search on a provider that cannot do it must not report the web was
    consulted."""

    text: str
    provider: str
    model_id: str
    web_used: bool = False
    sources: list[dict] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)


def _is_transient(exc: Exception) -> bool:
    """Read a status code off the exception first — providers that attach one
    (see `DeepSeekClient`) are unambiguous; fall back to substring matching
    for SDKs that only put it in the message. Guessing "transient" when it
    isn't costs one wasted retry; guessing "not transient" on a real blip
    costs the whole answer, so this defaults to the safer direction."""
    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)
    if isinstance(status, int):
        return status in _TRANSIENT_STATUSES
    message = str(exc)
    return any(token in message for token in _TRANSIENT_TOKENS)


class LLMClient(ABC):
    name: str = ""
    supports_web: bool = False

    @abstractmethod
    def ask(self, system: str, user: str, web: bool = False) -> Answer: ...

    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @staticmethod
    def _require(env_key: str, hint: str) -> str:
        from src.core.config import load_secrets  # adjust import to the project

        load_secrets()
        value = os.environ.get(env_key, "")
        if not value:
            raise LLMUnavailable(f"{env_key} is not set — {hint}")
        return value


class GeminiClient(LLMClient):
    """Default provider. Free tier, and the only one that grounds on the web
    without a second API key."""

    name = "gemini"
    supports_web = True
    _MODEL = "gemini-2.5-flash"  # PINNED — never *-latest, see PATTERNS.md §1

    def __init__(self) -> None:
        key = self._require("GEMINI_API_KEY", "add it to .secrets/.env")
        from google import genai  # deferred: only when this provider is active

        self._client = genai.Client(api_key=key)

    @property
    def model_id(self) -> str:
        return self._MODEL

    def ask(self, system: str, user: str, web: bool = False) -> Answer:
        from google.genai import types

        config: dict = {"system_instruction": system, "max_output_tokens": 8192}
        if web:
            config["tools"] = [types.Tool(google_search=types.GoogleSearch())]
        else:
            # gemini-2.5-flash is a thinking model and thinking tokens eat the
            # output budget, which shows up as an empty response
            # (finish_reason=MAX_TOKENS). Grounded calls need thinking
            # enabled, so this only applies to the ungrounded path.
            config["thinking_config"] = types.ThinkingConfig(thinking_budget=0)

        response = self._call(user, types.GenerateContentConfig(**config))
        text = self._text_of(response)
        return Answer(
            text=text,
            provider=self.name,
            model_id=self._MODEL,
            web_used=web,
            sources=self._sources_of(response) if web else [],
        )

    def _call(self, user: str, config):
        last: Exception | None = None
        for delay in (*_RETRY_BACKOFF, None):
            try:
                return self._client.models.generate_content(
                    model=self._MODEL, contents=user, config=config
                )
            except Exception as exc:  # noqa: BLE001 - SDK raises a wide family
                last = exc
                if delay is None or not _is_transient(exc):
                    raise LLMUnavailable(f"gemini: {exc}") from exc
                logger.info("gemini: transient error, retrying in %ss (%s)", delay, exc)
                time.sleep(delay)
        raise LLMUnavailable(f"gemini: {last}")

    @staticmethod
    def _text_of(response) -> str:
        text = getattr(response, "text", None)
        if text:
            return text
        try:  # empty or safety-blocked responses need the reason surfaced
            reason = response.candidates[0].finish_reason
        except (IndexError, AttributeError):
            reason = "unknown"
        raise LLMUnavailable(f"gemini returned no text (finish_reason={reason})")

    @staticmethod
    def _sources_of(response) -> list[dict]:
        """Citations behind a grounded answer. Best-effort: a missing or
        restructured grounding block costs the citations, not the answer."""
        out: list[dict] = []
        try:
            chunks = response.candidates[0].grounding_metadata.grounding_chunks or []
        except (IndexError, AttributeError):
            return out
        for chunk in chunks:
            web = getattr(chunk, "web", None)
            if web is not None:
                out.append(
                    {"title": getattr(web, "title", ""), "uri": getattr(web, "uri", "")}
                )
        return out


class DeepSeekClient(LLMClient):
    """OpenAI-compatible HTTP API. Attaches `status_code` to a raised error so
    `_is_transient` can read it structurally rather than pattern-matching a
    body every provider words differently."""

    name = "deepseek"
    supports_web = False
    _MODEL = "deepseek-chat"

    def __init__(self) -> None:
        key = self._require("DEEPSEEK_API_KEY", "add it to .secrets/.env")
        from openai import OpenAI  # deferred

        self._client = OpenAI(api_key=key, base_url="https://api.deepseek.com")

    @property
    def model_id(self) -> str:
        return self._MODEL

    def ask(self, system: str, user: str, web: bool = False) -> Answer:
        last: Exception | None = None
        for delay in (*_RETRY_BACKOFF, None):
            try:
                response = self._client.chat.completions.create(
                    model=self._MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )
                break
            except Exception as exc:  # noqa: BLE001 - SDK raises a wide family
                last = exc
                if delay is None or not _is_transient(exc):
                    raise LLMUnavailable(f"deepseek: {exc}") from exc
                time.sleep(delay)
        else:
            raise LLMUnavailable(f"deepseek: {last}")
        return Answer(
            text=response.choices[0].message.content or "",
            provider=self.name,
            model_id=self._MODEL,
            web_used=False,
        )


@contextmanager
def _without_anthropic_api_key():
    """Hide `ANTHROPIC_API_KEY` from the `claude` CLI for the duration of a
    call.

    The CLI resolves its own credentials and prefers an API key over the
    OAuth token when it can see one. With a zero-balance key visible, the CLI
    returned the literal string "Credit balance is too low" as the
    assistant's answer — a silent fallback dressed up as a valid reply, which
    is the worst of both worlds. Passing `env=` to the SDK is not enough: it
    is merged with the parent environment rather than replacing it (verified
    2026-08-01 on kite — the key still reached the child). So the variable is
    removed from this process for the duration and restored in `finally`,
    including on error."""
    sentinel = object()
    saved = os.environ.pop("ANTHROPIC_API_KEY", sentinel)
    try:
        yield
    finally:
        if saved is not sentinel:
            os.environ["ANTHROPIC_API_KEY"] = saved  # type: ignore[arg-type]


class ClaudeOAuthClient(LLMClient):
    """Claude via the Agent SDK, billed against the Claude Code subscription
    (`CLAUDE_CODE_OAUTH_TOKEN`) rather than metered API usage — the provider
    to use instead of a plain Anthropic API-key client (see module docstring).

    Runs the CLI headlessly with all tools disabled: this is a plain text
    Q&A call, not an agent session."""

    name = "claude"
    supports_web = False
    _MODEL = "claude-haiku-4-5-20251001"  # PINNED — never *-latest

    def __init__(self) -> None:
        self._require(
            "CLAUDE_CODE_OAUTH_TOKEN",
            "run `claude setup-token` and add it to .secrets/.env",
        )

    @property
    def model_id(self) -> str:
        return self._MODEL

    def ask(self, system: str, user: str, web: bool = False) -> Answer:
        import asyncio

        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            TextBlock,
            query,
        )

        options = ClaudeAgentOptions(
            system_prompt=system,
            model=self._MODEL,
            allowed_tools=[],
            mcp_servers={},
            permission_mode="bypassPermissions",
            # Not 1: the SDK counts the turn cap as an error result even when
            # the assistant already produced a complete answer, so
            # max_turns=1 fails every non-trivial question. 3 leaves headroom
            # without inviting an agent loop — there are no tools enabled for
            # it to loop over.
            max_turns=3,
        )

        async def _run() -> tuple[str, Exception | None]:
            """Drain the stream, keeping whatever text arrived even if the
            generator then raises.

            The SDK can raise `Claude Code returned an error result: success`
            *after* delivering a complete answer — observed 2026-08-01 with
            `is_error=False`, `subtype='success'` and a fully populated
            `result`. Treating that as a failure would throw away a good
            answer, so the text actually received decides the outcome, not
            the exception."""
            parts: list[str] = []
            try:
                async for message in query(prompt=user, options=options):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                parts.append(block.text)
            except Exception as exc:  # noqa: BLE001 - SDK/CLI raise a wide family
                return "".join(parts), exc
            return "".join(parts), None

        try:
            with _without_anthropic_api_key():
                text, streamed_error = asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001 - loop/spawn failures
            raise LLMUnavailable(f"claude: {exc}") from exc
        if not text.strip():
            reason = streamed_error or "empty response"
            raise LLMUnavailable(f"claude: {reason}")
        if streamed_error is not None:
            logger.info(
                "claude: answered, but the stream ended with %s", streamed_error
            )
        return Answer(
            text=text, provider=self.name, model_id=self._MODEL, web_used=False
        )


# Registry. Order is the UI's display order, and the first entry is the
# default. Deliberately no plain Anthropic API-key client — see the module
# docstring.
_PROVIDERS: dict[str, type[LLMClient]] = {
    "gemini": GeminiClient,
    "deepseek": DeepSeekClient,
    "claude": ClaudeOAuthClient,
}

_ENV_KEY = {
    "gemini": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "claude": "CLAUDE_CODE_OAUTH_TOKEN",
}


def provider_names() -> list[str]:
    return list(_PROVIDERS)


def get_client(provider: str | None = None) -> LLMClient:
    """Construct the named provider (default from config). Raises
    `LLMUnavailable` when it is unknown or its credential is missing."""
    name = (provider or DEFAULT_PROVIDER).lower()
    cls = _PROVIDERS.get(name)
    if cls is None:
        raise LLMUnavailable(
            f"Unknown LLM provider {name!r} — pick one of {provider_names()}"
        )
    return cls()


def provider_status() -> list[dict]:
    """One row per provider: is its credential present, what model would it
    use, can it search the web. Backs `GET /api/ask/providers` — the
    key-presence half of the two-endpoint rule (PATTERNS.md §1a). Deliberately
    does **not** call the provider; that's `POST /api/ask/test`."""
    from src.core.config import get_settings, load_secrets  # adjust to the project

    load_secrets()
    configured_default = (get_settings().llm_provider or DEFAULT_PROVIDER).lower()
    rows = []
    for name, cls in _PROVIDERS.items():
        rows.append(
            {
                "provider": name,
                "model_id": cls._MODEL,
                "configured": bool(os.environ.get(_ENV_KEY[name], "")),
                "env_key": _ENV_KEY[name],
                "supports_web": cls.supports_web,
                "is_default": name == configured_default,
            }
        )
    return rows
