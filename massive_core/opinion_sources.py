"""Turn real-world text into a simulation's initial opinion distribution.

``social_connectors.py`` could already score tweets and Reddit posts into
opinions in ``[-1, 1]``, but nothing consumed it: every simulation started from
``rng.uniform(...)``, so the connectors were an island. This module is the
missing wiring — it adapts any text corpus into the array
``energy_runner.run_energy_simulation`` integrates.

Design constraints that shaped this:

* **Optional means optional.** The default path needs no credentials and no
  network: :class:`CorpusSource` reads local text. ``tweepy``/``praw`` stay
  opt-in extras, and their absence is never fatal.
* **Deterministic.** Given the same texts and seed, the initial condition is
  bit-for-bit identical, so seeded runs stay reproducible.
* **No file paths over the API.** :class:`CorpusSource` takes a path because
  it is a local/CLI tool. The HTTP surface accepts *inline texts* only —
  accepting a path there would re-create the arbitrary-file-read hole that the
  removed ``api.py`` had to blocklist by hand.
"""

from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from social_connectors import _opinions_to_range, _score_text

__all__ = [
    "OpinionSample",
    "OpinionSource",
    "CorpusSource",
    "InlineTextSource",
    "ConnectorSource",
    "score_texts",
    "resample_opinions",
    "twitter_source_from_env",
    "reddit_source_from_env",
]

# A corpus bigger than this is almost certainly a mistaken argument (a whole
# dataset pointed at a simulation), and scoring is O(words).
MAX_DOCUMENTS = 100_000


@dataclass(frozen=True)
class OpinionSample:
    """An empirical opinion distribution extracted from text.

    Attributes:
        opinions: Scores already mapped into the engine's range.
        source: Human-readable provenance, surfaced in simulation output so a
            result can never be mistaken for a synthetic run.
        n_documents: How many texts produced the sample.
        range_type: ``"bipolar"`` or ``"unipolar"``.
        metadata: Source-specific extras (query, subreddit, path, ...).
    """

    opinions: np.ndarray
    source: str
    n_documents: int
    range_type: str = "bipolar"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def mean(self) -> float:
        return float(np.mean(self.opinions)) if self.opinions.size else 0.0

    @property
    def std(self) -> float:
        return float(np.std(self.opinions)) if self.opinions.size else 0.0

    def summary(self) -> dict[str, Any]:
        """Provenance block to attach to a simulation result."""
        return {
            "source": self.source,
            "n_documents": self.n_documents,
            "range_type": self.range_type,
            "mean_opinion": self.mean,
            "std_opinion": self.std,
            **self.metadata,
        }


class OpinionSource(Protocol):
    """Anything that can produce an :class:`OpinionSample`."""

    def sample(self, range_type: str = "bipolar") -> OpinionSample: ...


def score_texts(
    texts: list[str],
    range_type: str = "bipolar",
    source: str = "inline",
    metadata: dict[str, Any] | None = None,
) -> OpinionSample:
    """Score raw texts into an :class:`OpinionSample`.

    Empty and whitespace-only documents are dropped rather than scored as a
    neutral 0.0: a blank line is an absence of opinion, and counting it as
    "perfectly neutral" would drag the distribution toward the centre and
    understate polarization.
    """
    if len(texts) > MAX_DOCUMENTS:
        raise ValueError(f"corpus too large: {len(texts)} documents (max {MAX_DOCUMENTS})")

    kept = [t for t in texts if t and t.strip()]
    scores = np.array([_score_text(t) for t in kept], dtype=np.float64)
    opinions = _opinions_to_range(scores, range_type) if scores.size else scores

    return OpinionSample(
        opinions=opinions,
        source=source,
        n_documents=len(kept),
        range_type=range_type,
        metadata=metadata or {},
    )


def resample_opinions(
    sample: OpinionSample,
    n_agents: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Resize an empirical distribution to exactly ``n_agents`` values.

    A corpus rarely has exactly as many documents as the simulation has
    agents. Drawing *with replacement* in both directions keeps the shape of
    the empirical distribution (including its bimodality, which is the whole
    point of seeding from real opinion) instead of fitting a Gaussian to it.

    Raises:
        ValueError: if the sample is empty. Falling back to a uniform draw
            would silently turn a "seeded from real data" run into a synthetic
            one, which is exactly the kind of invisible degradation this
            codebase treats as a bug.
    """
    if sample.opinions.size == 0:
        raise ValueError(
            "cannot seed a simulation from an empty opinion sample "
            f"(source={sample.source!r}); supply documents or use the "
            "default uniform initialisation explicitly"
        )
    if n_agents < 1:
        raise ValueError(f"n_agents must be >= 1, got {n_agents}")

    idx = rng.integers(0, sample.opinions.size, size=n_agents)
    return sample.opinions[idx].astype(np.float64, copy=True)


class InlineTextSource:
    """Opinions from texts held in memory — the API-safe source."""

    def __init__(self, texts: list[str], label: str = "inline") -> None:
        self._texts = list(texts)
        self._label = label

    def sample(self, range_type: str = "bipolar") -> OpinionSample:
        return score_texts(self._texts, range_type=range_type, source=self._label)


class CorpusSource:
    """Opinions from a local text corpus. No credentials, no network.

    Supported formats, chosen by extension:
      ``.txt``   one document per line
      ``.jsonl`` one JSON object per line; uses ``text_field``
      ``.csv``   uses the ``text_field`` column
    """

    def __init__(self, path: str | Path, text_field: str = "text") -> None:
        self.path = Path(path)
        self.text_field = text_field

    def _read(self) -> list[str]:
        if not self.path.exists():
            raise FileNotFoundError(f"corpus not found: {self.path}")

        suffix = self.path.suffix.lower()
        if suffix == ".txt":
            return self.path.read_text(encoding="utf-8").splitlines()

        if suffix == ".jsonl":
            texts: list[str] = []
            for lineno, line in enumerate(
                self.path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{self.path}:{lineno}: invalid JSON: {exc}") from exc
                if self.text_field not in obj:
                    raise ValueError(
                        f"{self.path}:{lineno}: missing field {self.text_field!r}; "
                        f"available: {sorted(obj)}"
                    )
                texts.append(str(obj[self.text_field]))
            return texts

        if suffix == ".csv":
            with self.path.open(encoding="utf-8", newline="") as fh:
                reader = csv.DictReader(fh)
                if reader.fieldnames is None or self.text_field not in reader.fieldnames:
                    raise ValueError(
                        f"{self.path}: missing column {self.text_field!r}; "
                        f"available: {reader.fieldnames}"
                    )
                return [str(row[self.text_field] or "") for row in reader]

        raise ValueError(f"unsupported corpus format {suffix!r} (use .txt, .jsonl or .csv)")

    def sample(self, range_type: str = "bipolar") -> OpinionSample:
        return score_texts(
            self._read(),
            range_type=range_type,
            source=f"corpus:{self.path.name}",
            metadata={"path": str(self.path)},
        )


class ConnectorSource:
    """Adapts a live ``social_connectors`` client to :class:`OpinionSource`.

    Kept deliberately thin: the connectors already return the opinion array,
    so this only normalises their differing dict shapes (``n_tweets`` vs
    ``n_posts``) into one type. Requires credentials and network, so it is
    never on the default path.
    """

    def __init__(self, connector: Any, label: str, **fetch_kwargs: Any) -> None:
        self._connector = connector
        self._label = label
        self._fetch_kwargs = fetch_kwargs

    def sample(self, range_type: str = "bipolar") -> OpinionSample:
        result = self._connector.fetch_opinions(range_type=range_type, **self._fetch_kwargs)
        opinions = np.asarray(result["opinions"], dtype=np.float64)
        n_docs = int(result.get("n_tweets", result.get("n_posts", opinions.size)))
        metadata = {k: v for k, v in result.items() if k not in {"opinions", "n_tweets", "n_posts"}}
        return OpinionSample(
            opinions=opinions,
            source=self._label,
            n_documents=n_docs,
            range_type=range_type,
            metadata=metadata,
        )


# --- Credentials from the environment ------------------------------------
#
# `.env.example` has shipped TWITTER_BEARER_TOKEN, REDDIT_CLIENT_ID and
# REDDIT_CLIENT_SECRET for a long time, but nothing read them: setting them
# did literally nothing. These two helpers make the documented configuration
# real. Both return None rather than raising when credentials are absent, so
# "optional means optional" holds and callers can fall back to a corpus.


def twitter_source_from_env(query: str, **kwargs: Any) -> ConnectorSource | None:
    """Build a Twitter-backed source from ``TWITTER_BEARER_TOKEN``.

    Returns:
        ``None`` when the token is unset or ``tweepy`` is not installed.
    """
    token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    if not token:
        return None
    try:
        from social_connectors import TwitterConnector
    except ImportError:  # pragma: no cover - import guard
        return None
    try:
        connector = TwitterConnector(bearer_token=token)
    except (ImportError, ValueError):
        # tweepy missing, or the token is present but unusable. Degrade to the
        # default path instead of taking the whole simulation down.
        return None
    return ConnectorSource(connector, label=f"twitter:{query}", query=query, **kwargs)


def reddit_source_from_env(
    subreddit_name: str, query: str, **kwargs: Any
) -> ConnectorSource | None:
    """Build a Reddit-backed source from ``REDDIT_CLIENT_ID``/``_SECRET``.

    Returns:
        ``None`` when either credential is unset or ``praw`` is not installed.
    """
    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    try:
        from social_connectors import RedditConnector
    except ImportError:  # pragma: no cover - import guard
        return None
    try:
        connector = RedditConnector(client_id=client_id, client_secret=client_secret)
    except (ImportError, ValueError):
        return None
    return ConnectorSource(
        connector,
        label=f"reddit:r/{subreddit_name}",
        subreddit_name=subreddit_name,
        query=query,
        **kwargs,
    )
