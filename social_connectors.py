"""
social_connectors.py — Conectores de redes sociales para MASSIVE
Soporta: Twitter/X (tweepy v4) y Reddit (praw).
Credenciales configurables por el usuario en la UI.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import numpy as np

log = logging.getLogger("massive")

# ── Importaciones opcionales ──────────────────────────────────────────────────
try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False


# ─────────────────────────────────────────────────────────────────────────────
# ANÁLISIS DE SENTIMIENTO LIGERO (sin dependencias extra)
# Simple keyword-based sentiment scorer returning [-1, 1].
# ─────────────────────────────────────────────────────────────────────────────

_POSITIVE_WORDS = {
    "love", "great", "excellent", "good", "awesome", "best", "happy", "support",
    "agree", "yes", "win", "success", "positive", "amazing", "wonderful", "like",
    "thanks", "thank", "perfect", "brilliant", "hope", "trust", "unite", "peace",
    "bueno", "excelente", "amor", "apoya", "feliz", "genial", "gracias", "bien",
    "acuerdo", "progreso", "unidad", "paz", "confianza",
}
_NEGATIVE_WORDS = {
    "hate", "bad", "awful", "terrible", "worst", "corrupt", "lie", "liar", "fake",
    "no", "fail", "crisis", "wrong", "against", "reject", "disgrace", "fear",
    "angry", "sad", "unfair", "protest", "violence", "evil", "fraud", "scam",
    "malo", "odio", "corrupción", "mentira", "fraude", "crisis", "miedo", "triste",
    "rechazo", "protesta", "violencia", "injusto",
}

def _score_text(text: str) -> float:
    """
    Returns a sentiment score in [-1, 1] for the given text.
    Positive = +1, Negative = -1, Mixed/Neutral = 0.
    """
    words = re.findall(r"\w+", text.lower())
    pos = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return float((pos - neg) / total)


def _opinions_to_range(scores: np.ndarray, range_type: str = "bipolar") -> np.ndarray:
    """
    Convert [-1, 1] sentiment scores to the simulator's opinion range.
    bipolar: [-1, 1] unchanged.
    unipolar: mapped to [0, 1].
    """
    if range_type == "unipolar":
        return np.clip((scores + 1.0) / 2.0, 0.0, 1.0)
    return np.clip(scores, -1.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# TWITTER / X CONNECTOR
# ─────────────────────────────────────────────────────────────────────────────

class TwitterConnector:
    """
    Fetches recent tweets matching a search query and converts them to
    opinion scores using lightweight sentiment analysis.

    Uses Twitter API v2 (tweepy.Client). Requires a Bearer Token at minimum.
    """

    def __init__(
        self,
        bearer_token: str,
        consumer_key: str = "",
        consumer_secret: str = "",
        access_token: str = "",
        access_token_secret: str = "",
    ) -> None:
        if not TWEEPY_AVAILABLE:
            raise ImportError("tweepy no está instalado. Ejecuta: pip install tweepy>=4.16.0")
        if not bearer_token.strip():
            raise ValueError("Se requiere un Bearer Token de Twitter/X.")

        self.client = tweepy.Client(
            bearer_token=bearer_token.strip(),
            consumer_key=consumer_key.strip() or None,
            consumer_secret=consumer_secret.strip() or None,
            access_token=access_token.strip() or None,
            access_token_secret=access_token_secret.strip() or None,
            wait_on_rate_limit=True,
        )
        log.info("[Twitter] Cliente inicializado.")

    def fetch_opinions(
        self,
        query: str,
        max_results: int = 100,
        range_type: str = "bipolar",
        lang: str = "en",
    ) -> dict:
        """
        Search recent tweets for ``query`` and return opinion statistics.

        Args:
            query: Twitter search query string.
            max_results: Number of tweets to fetch (10–100 per API call, free tier limit).
            range_type: "bipolar" [-1,1] or "unipolar" [0,1].
            lang: BCP-47 language code for tweet language filter (default "en").
                  Set to "" to disable the language filter and search all languages.

        Returns:
            dict with keys: opinions, mean_opinion, std_opinion, n_tweets, query.
        """
        max_results = int(np.clip(max_results, 10, 100))
        lang_filter = f" lang:{lang}" if lang.strip() else ""
        query_safe = f"{query}{lang_filter} -is:retweet"
        try:
            response = self.client.search_recent_tweets(
                query=query_safe,
                max_results=max_results,
                tweet_fields=["text", "public_metrics"],
            )
        except Exception as exc:
            raise RuntimeError(f"[Twitter] Error al buscar tweets: {exc}") from exc

        if not response.data:
            return {
                "opinions": np.array([]),
                "mean_opinion": 0.0,
                "std_opinion": 0.0,
                "n_tweets": 0,
                "query": query,
            }

        raw_scores = np.array([_score_text(t.text) for t in response.data])
        opinions = _opinions_to_range(raw_scores, range_type)

        return {
            "opinions": opinions,
            "mean_opinion": float(np.mean(opinions)),
            "std_opinion": float(np.std(opinions)),
            "n_tweets": len(opinions),
            "query": query,
        }


# ─────────────────────────────────────────────────────────────────────────────
# REDDIT CONNECTOR
# ─────────────────────────────────────────────────────────────────────────────

class RedditConnector:
    """
    Fetches posts/comments from a subreddit and converts them to opinion scores.

    Uses praw (Python Reddit API Wrapper). Requires client_id + client_secret.
    Score-based weighting uses the Reddit vote score to amplify or dampen
    each post's sentiment.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str = "MASSIVE/1.0",
        username: str = "",
        password: str = "",
    ) -> None:
        if not PRAW_AVAILABLE:
            raise ImportError("praw no está instalado. Ejecuta: pip install praw>=7.8.1")
        if not client_id.strip() or not client_secret.strip():
            raise ValueError("Se requieren client_id y client_secret de Reddit.")

        kwargs: dict = {
            "client_id": client_id.strip(),
            "client_secret": client_secret.strip(),
            "user_agent": user_agent,
        }
        if username.strip() and password.strip():
            kwargs["username"] = username.strip()
            kwargs["password"] = password.strip()

        self.reddit = praw.Reddit(**kwargs)
        log.info("[Reddit] Cliente inicializado.")

    def fetch_opinions(
        self,
        subreddit_name: str,
        query: str,
        limit: int = 100,
        range_type: str = "bipolar",
        sort: str = "relevance",
    ) -> dict:
        """
        Search ``subreddit_name`` for posts matching ``query`` and return
        opinion statistics weighted by Reddit vote score.

        Args:
            subreddit_name: Subreddit name without 'r/' prefix.
            query: Search query string.
            limit: Maximum number of posts to fetch (max 100).
            range_type: "bipolar" or "unipolar".
            sort: Reddit sort ("relevance", "hot", "new", "top").

        Returns:
            dict with keys: opinions, mean_opinion, std_opinion, n_posts,
            subreddit, query.
        """
        limit = int(np.clip(limit, 1, 100))
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            results = list(subreddit.search(query, sort=sort, limit=limit))
        except Exception as exc:
            raise RuntimeError(f"[Reddit] Error al buscar en r/{subreddit_name}: {exc}") from exc

        if not results:
            return {
                "opinions": np.array([]),
                "mean_opinion": 0.0,
                "std_opinion": 0.0,
                "n_posts": 0,
                "subreddit": subreddit_name,
                "query": query,
            }

        raw_scores = []
        weights = []
        for post in results:
            text = f"{post.title} {post.selftext or ''}"
            sentiment = _score_text(text)
            raw_scores.append(sentiment)
            weights.append(abs(post.score) + 1)

        raw_scores = np.array(raw_scores, dtype=float)
        weights = np.array(weights, dtype=float)
        weights /= weights.sum()

        opinions = _opinions_to_range(raw_scores, range_type)
        weighted_mean = float(np.sum(opinions * weights))
        weighted_std  = float(np.sqrt(np.sum(weights * (opinions - weighted_mean) ** 2)))

        return {
            "opinions": opinions,
            "mean_opinion": weighted_mean,
            "std_opinion": weighted_std,
            "n_posts": len(opinions),
            "subreddit": subreddit_name,
            "query": query,
        }
