"""Seeding a simulation from real opinion data.

``social_connectors`` could score text into opinions but nothing consumed it:
every run started from ``rng.uniform(...)``. These tests cover the wiring that
closes that gap, and in particular the properties that make it trustworthy —
determinism, honest provenance, loud failure, and no file-path intake on the
HTTP surface.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from massive_core.opinion_sources import (
    CorpusSource,
    InlineTextSource,
    OpinionSample,
    resample_opinions,
    score_texts,
)

POSITIVE = "I love this, it is great and excellent news"
NEGATIVE = "terrible awful fraud, I hate this corrupt lie"
NEUTRAL = "the meeting is scheduled for five o'clock"


class TestScoring:
    def test_polarised_corpus_yields_a_bimodal_distribution(self):
        sample = score_texts([POSITIVE] * 5 + [NEGATIVE] * 5)
        assert sample.n_documents == 10
        assert sample.mean == pytest.approx(0.0, abs=1e-12)
        # The point of seeding from data: the two camps survive. A Gaussian
        # fit or a uniform draw would wash this out.
        assert sample.std > 0.9
        assert set(np.unique(sample.opinions)) == {-1.0, 1.0}

    def test_blank_documents_are_dropped_not_scored_as_neutral(self):
        """A blank line is an absence of opinion. Scoring it as 0.0 would drag
        the distribution to the centre and understate polarization."""
        sample = score_texts([POSITIVE, "", "   ", "\n", NEGATIVE])
        assert sample.n_documents == 2
        assert sample.std == pytest.approx(1.0)

    def test_unipolar_range_is_respected(self):
        sample = score_texts([POSITIVE, NEGATIVE], range_type="unipolar")
        assert sample.opinions.min() >= 0.0
        assert sample.opinions.max() <= 1.0

    def test_neutral_text_scores_zero(self):
        assert score_texts([NEUTRAL]).opinions.tolist() == [0.0]

    def test_oversized_corpus_is_refused(self):
        with pytest.raises(ValueError, match="corpus too large"):
            score_texts(["x"] * 100_001)


class TestResampling:
    def test_is_deterministic_for_a_given_seed(self):
        sample = score_texts([POSITIVE] * 3 + [NEGATIVE] * 3)
        a = resample_opinions(sample, 50, np.random.default_rng(11))
        b = resample_opinions(sample, 50, np.random.default_rng(11))
        assert np.array_equal(a, b)

    def test_different_seeds_give_different_draws(self):
        sample = score_texts([POSITIVE] * 3 + [NEGATIVE] * 3)
        a = resample_opinions(sample, 50, np.random.default_rng(1))
        b = resample_opinions(sample, 50, np.random.default_rng(2))
        assert not np.array_equal(a, b)

    def test_upsamples_and_downsamples_to_exactly_n_agents(self):
        sample = score_texts([POSITIVE] * 4 + [NEGATIVE] * 4)
        for n in (1, 3, 8, 500):
            assert resample_opinions(sample, n, np.random.default_rng(0)).shape == (n,)

    def test_preserves_the_empirical_distribution(self):
        """Resampling must not quietly reshape the data it was given."""
        sample = score_texts([POSITIVE] * 7 + [NEGATIVE] * 3)
        drawn = resample_opinions(sample, 20_000, np.random.default_rng(5))
        assert drawn.mean() == pytest.approx(sample.mean, abs=0.02)
        assert drawn.std() == pytest.approx(sample.std, abs=0.02)

    def test_empty_sample_fails_loudly(self):
        """Falling back to uniform would report a data-seeded run that was in
        fact synthetic — the kind of silent degradation this repo treats as a
        bug."""
        empty = OpinionSample(opinions=np.array([]), source="nothing", n_documents=0)
        with pytest.raises(ValueError, match="empty opinion sample"):
            resample_opinions(empty, 10, np.random.default_rng(0))

    def test_rejects_nonpositive_agent_count(self):
        sample = score_texts([POSITIVE])
        with pytest.raises(ValueError, match="n_agents"):
            resample_opinions(sample, 0, np.random.default_rng(0))


class TestCorpusSource:
    """Local files only — no credentials, no network."""

    def test_reads_txt(self, tmp_path):
        path = tmp_path / "c.txt"
        path.write_text(f"{POSITIVE}\n{NEGATIVE}\n", encoding="utf-8")
        sample = CorpusSource(path).sample()
        assert sample.n_documents == 2
        assert sample.source == "corpus:c.txt"

    def test_reads_jsonl(self, tmp_path):
        path = tmp_path / "c.jsonl"
        path.write_text(
            "\n".join(json.dumps({"text": t}) for t in (POSITIVE, NEGATIVE)),
            encoding="utf-8",
        )
        assert CorpusSource(path).sample().n_documents == 2

    def test_reads_csv(self, tmp_path):
        path = tmp_path / "c.csv"
        path.write_text(f"id,text\n1,{POSITIVE}\n2,{NEGATIVE}\n", encoding="utf-8")
        assert CorpusSource(path).sample().n_documents == 2

    def test_missing_file_is_explicit(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="corpus not found"):
            CorpusSource(tmp_path / "nope.txt").sample()

    def test_unsupported_format_names_the_alternatives(self, tmp_path):
        path = tmp_path / "c.parquet"
        path.write_text("x", encoding="utf-8")
        with pytest.raises(ValueError, match=r"\.txt, \.jsonl or \.csv"):
            CorpusSource(path).sample()

    def test_missing_field_reports_what_is_available(self, tmp_path):
        path = tmp_path / "c.jsonl"
        path.write_text(json.dumps({"body": POSITIVE}), encoding="utf-8")
        with pytest.raises(ValueError, match="missing field 'text'"):
            CorpusSource(path).sample()

    def test_malformed_jsonl_points_at_the_line(self, tmp_path):
        path = tmp_path / "c.jsonl"
        path.write_text(json.dumps({"text": POSITIVE}) + "\nnot json\n", encoding="utf-8")
        with pytest.raises(ValueError, match=r"c\.jsonl:2"):
            CorpusSource(path).sample()


class TestConnectorAdapter:
    """The live connectors stay opt-in, but the adapter must normalise them."""

    class _FakeTwitter:
        def fetch_opinions(self, range_type="bipolar", **kw):
            return {
                "opinions": np.array([1.0, -1.0]),
                "mean_opinion": 0.0,
                "std_opinion": 1.0,
                "n_tweets": 2,
                "query": kw.get("query", ""),
            }

    def test_normalises_n_tweets_into_n_documents(self):
        from massive_core.opinion_sources import ConnectorSource

        src = ConnectorSource(self._FakeTwitter(), label="twitter", query="brexit")
        sample = src.sample()
        assert sample.n_documents == 2
        assert sample.source == "twitter"
        assert sample.metadata["query"] == "brexit"


class TestEngineWiring:
    """End-to-end: a corpus actually changes the simulated initial condition."""

    @staticmethod
    def _run(**kw):
        pytest.importorskip("networkx")
        from energy_runner import run_energy_simulation

        return run_energy_simulation(
            user_goal="social polarization", n_agents=40, steps=5, seed=7, **kw
        )

    def test_default_run_reports_uniform_provenance(self):
        result = self._run()
        assert result["initial_conditions"]["source"] == "uniform"

    def test_seeded_run_reports_its_provenance(self):
        texts = [POSITIVE] * 8 + [NEGATIVE] * 8
        result = self._run(opinion_source=InlineTextSource(texts))
        ic = result["initial_conditions"]
        assert ic["source"] == "inline"
        assert ic["n_documents"] == 16
        # A consumer must be able to tell this apart from a synthetic run.
        assert ic["std_opinion"] == pytest.approx(1.0)

    def test_data_seeding_is_reproducible(self):
        texts = [POSITIVE] * 5 + [NEGATIVE] * 5
        a = self._run(opinion_source=InlineTextSource(texts))
        b = self._run(opinion_source=InlineTextSource(texts))
        assert a["summary"]["opinion_inicial"] == b["summary"]["opinion_inicial"]
        assert a["final_state"]["opinions"] == b["final_state"]["opinions"]

    def test_real_data_preserves_polarization_a_uniform_draw_destroys(self):
        texts = [POSITIVE] * 10 + [NEGATIVE] * 10
        seeded = self._run(opinion_source=InlineTextSource(texts))
        uniform = self._run()
        # Bimodal +/-1 data has std ~1.0; a uniform draw on [-1,1] has ~0.577.
        assert seeded["history"][0]["std_opinion"] > 0.85
        assert uniform["history"][0]["std_opinion"] < 0.75


class TestHttpSurfaceIsSafe:
    """The API takes texts, never a location to read them from."""

    @staticmethod
    def _client():
        pytest.importorskip("networkx")
        import os

        from fastapi.testclient import TestClient

        os.environ["MASSIVE_ENV"] = "development"
        os.environ["MASSIVE_API_KEY"] = "testkey-opinion"
        from backend.app.main import app

        return TestClient(app)

    def test_inline_texts_seed_the_run(self):
        client = self._client()
        body = {
            "user_goal": "polarization",
            "n_agents": 30,
            "steps": 3,
            "seed": 3,
            "opinion_texts": [POSITIVE] * 8 + [NEGATIVE] * 8,
        }
        resp = client.post("/v1/engine/energy", json=body, headers={"X-API-Key": "testkey-opinion"})
        assert resp.status_code == 200, resp.text
        ic = resp.json()["initial_conditions"]
        assert ic["source"] == "api:inline"
        assert ic["n_documents"] == 16

    def test_omitting_texts_still_works(self):
        client = self._client()
        resp = client.post(
            "/v1/engine/energy",
            json={"user_goal": "x", "n_agents": 20, "steps": 2},
            headers={"X-API-Key": "testkey-opinion"},
        )
        assert resp.status_code == 200
        assert resp.json()["initial_conditions"]["source"] == "uniform"

    @pytest.mark.parametrize(
        "field", ["opinion_corpus_path", "corpus_path", "opinion_url", "file_path"]
    )
    def test_no_way_to_point_the_api_at_a_location(self, field):
        """Guards the lesson from the removed `api.py`: a path field here is
        an arbitrary-file-read primitive."""
        client = self._client()
        resp = client.post(
            "/v1/engine/energy",
            json={"user_goal": "x", field: "/etc/passwd"},
            headers={"X-API-Key": "testkey-opinion"},
        )
        assert resp.status_code == 422
