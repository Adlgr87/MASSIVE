"""Tests for the MASSIVE Ground Truth Data Layer (Layer 1).

Verifies:
* Synthetic microdata has expected columns, valid opinion ranges, and
  representative demographic distributions.
* Network topology metrics cover all required keys with valid ranges.
* Timeseries Parquet files load correctly with embedded metadata.
* Splits are deterministic (same seed → same splits).
* The historical-test split is sealed and not accessible without an
  explicit unlock key.

Run with::

    pytest tests/test_ground_truth_layer.py -v
"""

from __future__ import annotations

import hashlib
import json

import pandas as pd
import pyarrow.parquet as pq
import pytest

from ground_truth import (
    DATASETS_DIR,
    HistoricalTestSealedError,
    MICRODATA_DICT_PATH,
    MICRODATA_N_AGENTS,
    MICRODATA_PATH,
    MICRODATA_SEED,
    NETWORK_PATH,
    PROVENANCE_PATH,
    SPLITS_PATH,
    SPLITS_SEED,
    derive_unlock_key,
    get_split,
    list_timeseries_events,
    load_microdata,
    load_network_topology,
    load_timeseries,
    load_variable_dictionary,
    seal_splits,
    unlock_historical_test,
    verify_seal,
)
from ground_truth import load_timeseries_metadata

# ── Fixtures ────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def microdata() -> pd.DataFrame:
    """Load microdata once for the entire module."""
    return load_microdata()


@pytest.fixture(scope="module")
def network_metrics() -> dict:
    """Load network topology metrics."""
    return load_network_topology()


@pytest.fixture(scope="module")
def splits() -> dict:
    """Load the sealed splits definition."""
    with open(SPLITS_PATH, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def provenance() -> dict:
    """Load the provenance registry."""
    with open(PROVENANCE_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── 1. Microdata ────────────────────────────────────────────────────────


class TestMicrodata:
    """Verify synthetic census microdata structure and contents."""

    EXPECTED_COLUMNS = [
        "agent_id",
        "age_group",
        "education_level",
        "income_quintile",
        "gender",
        "region",
        "cultural_profile",
        "opinion_baseline",
    ]

    def test_file_exists(self):
        """Microdata parquet file should exist."""
        assert MICRODATA_PATH.exists(), f"Missing {MICRODATA_PATH}"

    def test_expected_columns(self, microdata: pd.DataFrame):
        """All required columns must be present."""
        for col in self.EXPECTED_COLUMNS:
            assert col in microdata.columns, f"Missing column: {col}"

    def test_n_agents(self, microdata: pd.DataFrame):
        """Should contain the expected number of agents."""
        assert len(microdata) == MICRODATA_N_AGENTS

    def test_agent_ids_unique(self, microdata: pd.DataFrame):
        """Agent IDs must be unique and sequential."""
        ids = microdata["agent_id"]
        assert ids.is_unique
        assert ids.min() == 0
        assert ids.max() == MICRODATA_N_AGENTS - 1

    def test_opinion_in_range(self, microdata: pd.DataFrame):
        """All opinion_baseline values must be in [-1, 1]."""
        import numpy as np
        opinions = microdata["opinion_baseline"].to_numpy()
        assert np.all(opinions >= -1.0), "Opinion below -1.0 found"
        assert np.all(opinions <= 1.0), "Opinion above 1.0 found"

    def test_opinion_is_numeric(self, microdata: pd.DataFrame):
        """opinion_baseline must be a numeric float column."""
        assert pd.api.types.is_float_dtype(microdata["opinion_baseline"])

    def test_age_group_categories(self, microdata: pd.DataFrame):
        """Age groups must match the variable dictionary."""
        var_dict = load_variable_dictionary()
        expected = set(var_dict["variables"]["age_group"]["categories"])
        actual = set(microdata["age_group"].unique())
        assert actual.issubset(expected), f"Unexpected age groups: {actual - expected}"

    def test_education_categories(self, microdata: pd.DataFrame):
        """Education levels must match the variable dictionary."""
        var_dict = load_variable_dictionary()
        expected = set(var_dict["variables"]["education_level"]["categories"])
        actual = set(microdata["education_level"].unique())
        assert actual.issubset(expected)

    def test_income_quintile_categories(self, microdata: pd.DataFrame):
        """Income quintiles must match the variable dictionary."""
        var_dict = load_variable_dictionary()
        expected = set(var_dict["variables"]["income_quintile"]["categories"])
        actual = set(microdata["income_quintile"].unique())
        assert actual.issubset(expected)

    def test_gender_categories(self, microdata: pd.DataFrame):
        """Gender must match the variable dictionary."""
        var_dict = load_variable_dictionary()
        expected = set(var_dict["variables"]["gender"]["categories"])
        actual = set(microdata["gender"].unique())
        assert actual.issubset(expected)

    def test_cultural_profile_categories(self, microdata: pd.DataFrame):
        """Cultural profiles must match the variable dictionary."""
        var_dict = load_variable_dictionary()
        expected = set(var_dict["variables"]["cultural_profile"]["categories"])
        actual = set(microdata["cultural_profile"].unique())
        assert actual.issubset(expected)

    def test_marginal_distributions(self, microdata: pd.DataFrame):
        """Demographic marginals should approximate target distributions.

        Uses a loose tolerance (±10 pp) to account for IPF sampling noise.
        """
        income_counts = microdata["income_quintile"].value_counts(normalize=True)
        for q in ["Q1", "Q2", "Q3", "Q4", "Q5"]:
            assert abs(income_counts.get(q, 0) - 0.20) < 0.10, (
                f"Income quintile {q}: {income_counts.get(q, 0):.3f} vs 0.200"
            )

    def test_opinion_distribution_reasonable(self, microdata: pd.DataFrame):
        """Opinion distribution should be centred near 0 with spread."""
        import numpy as np
        opinions = microdata["opinion_baseline"].to_numpy()
        mean = float(np.mean(opinions))
        std = float(np.std(opinions))
        assert abs(mean) < 0.30, f"Opinion mean too extreme: {mean:.4f}"
        assert std > 0.05, f"Opinion std too low: {std:.4f}"

    def test_variable_dictionary_exists(self):
        """Variable dictionary JSON should exist."""
        assert MICRODATA_DICT_PATH.exists()

    def test_variable_dictionary_valid(self):
        """Variable dictionary should have all required fields."""
        var_dict = load_variable_dictionary()
        assert "variables" in var_dict
        for col in self.EXPECTED_COLUMNS:
            assert col in var_dict["variables"], f"Missing variable in dict: {col}"
            var = var_dict["variables"][col]
            assert "type" in var
            assert "description" in var
            assert "source" in var

    def test_parquet_metadata(self, microdata: pd.DataFrame):
        """Parquet file should have embedded metadata."""
        table = pq.read_table(str(MICRODATA_PATH))
        meta = table.schema.metadata
        assert meta is not None
        assert b"method" in meta or "method" in meta


# ── 2. Network topology ────────────────────────────────────────────────


class TestNetworkTopology:
    """Verify network topology metrics structure and ranges."""

    def test_file_exists(self):
        assert NETWORK_PATH.exists()

    def test_has_metadata(self, network_metrics: dict):
        assert "metadata" in network_metrics
        meta = network_metrics["metadata"]
        assert "n_nodes" in meta
        assert "n_edges" in meta
        assert "seed" in meta
        assert "references" in meta

    def test_has_all_required_metrics(self, network_metrics: dict):
        required = [
            "degree_distribution",
            "clustering_coefficient",
            "modularity",
            "echo_chamber_density",
            "influence_asymmetry",
        ]
        for key in required:
            assert key in network_metrics, f"Missing metric: {key}"

    def test_degree_distribution(self, network_metrics: dict):
        dd = network_metrics["degree_distribution"]
        assert "gamma" in dd
        assert "xmin" in dd
        assert "method" in dd
        assert "sources" in dd
        gamma = dd["gamma"]
        assert 1.5 <= gamma <= 3.5, f"gamma out of range: {gamma}"
        assert dd["xmin"] >= 1

    def test_clustering_coefficient(self, network_metrics: dict):
        cc = network_metrics["clustering_coefficient"]
        assert "global" in cc
        assert "by_degree_bin" in cc
        assert "method" in cc
        assert "sources" in cc
        assert 0.0 <= cc["global"] <= 1.0
        for bin_name, val in cc["by_degree_bin"].items():
            assert 0.0 <= val <= 1.0, f"Clustering for {bin_name} out of range: {val}"

    def test_modularity(self, network_metrics: dict):
        mod = network_metrics["modularity"]
        assert "value" in mod
        assert "method" in mod
        assert "sources" in mod
        assert 0.0 <= mod["value"] <= 1.0, f"Modularity out of range: {mod['value']}"

    def test_echo_chamber_density(self, network_metrics: dict):
        ec = network_metrics["echo_chamber_density"]
        assert "intra_community_edge_ratio" in ec or "intra_to_inter_ratio" in ec
        assert "method" in ec
        assert "sources" in ec
        intra = ec.get("intra_community_edge_ratio", 0.0)
        inter = ec.get("inter_community_edge_ratio", 0.0)
        assert 0.0 <= intra <= 1.0
        assert 0.0 <= inter <= 1.0
        assert intra + inter == pytest.approx(1.0, abs=0.01)

    def test_influence_asymmetry(self, network_metrics: dict):
        ia = network_metrics["influence_asymmetry"]
        assert "authority_weight_distribution" in ia
        assert "method" in ia
        assert "sources" in ia
        awd = ia["authority_weight_distribution"]
        assert "gini_coefficient" in awd
        assert 0.0 <= awd["gini_coefficient"] <= 1.0
        assert "follower_to_influencer_ratio" in ia

    def test_all_metrics_have_sources(self, network_metrics: dict):
        """Every metric section should reference empirical sources."""
        for key in [
            "degree_distribution",
            "clustering_coefficient",
            "modularity",
            "echo_chamber_density",
            "influence_asymmetry",
        ]:
            section = network_metrics[key]
            assert "sources" in section, f"No sources for {key}"
            assert len(section["sources"]) > 0, f"Empty sources for {key}"


# ── 3. Timeseries parquet ──────────────────────────────────────────────


class TestTimeseries:
    """Verify timeseries Parquet conversions."""

    EXPECTED_EVENTS = [
        "brazil_election_2022",
        "brexit_referendum_2016",
        "chile_estallido_2019",
        "colombia_paro_2021",
        "egypt_arab_spring_2011",
        "france_gilets_jaunes_2018",
        "germany_pegida_2014",
        "hong_kong_protests_2019",
        "iran_mahsa_amini_2022",
        "myanmar_coup_cdm_2021",
        "south_korea_candlelight_2016",
        "us_election_2020",
    ]

    def test_all_events_present(self):
        """All 11 real-case events should have parquet files."""
        events = list_timeseries_events()
        for expected in self.EXPECTED_EVENTS:
            assert expected in events, f"Missing event: {expected}"

    def test_load_valid_event(self):
        """Loading a valid event should return a DataFrame."""
        df = load_timeseries("brexit_referendum_2016")
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_columns_correct(self):
        """Timeseries DataFrame should have expected columns."""
        df = load_timeseries("brexit_referendum_2016")
        assert "timestep" in df.columns
        assert "date" in df.columns
        assert "polarization" in df.columns

    def test_polarization_numeric_and_range(self):
        """Polarization values should be numeric and in [0, 1]."""
        df = load_timeseries("us_election_2020")
        assert pd.api.types.is_numeric_dtype(df["polarization"])
        assert df["polarization"].min() >= 0.0
        assert df["polarization"].max() <= 1.0

    def test_timestep_sequential(self):
        """Timestep column should be 0-indexed and sequential."""
        df = load_timeseries("brexit_referendum_2016")
        assert df["timestep"].tolist() == list(range(len(df)))

    def test_date_sorted(self):
        """Dates should be sorted chronologically."""
        df = load_timeseries("brexit_referendum_2016")
        dates = df["date"].tolist()
        assert dates == sorted(dates)

    def test_hong_kong_year_correction(self):
        """The 2016->2019 typo in Hong Kong data should be fixed."""
        df = load_timeseries("hong_kong_protests_2019")
        dates = df["date"].tolist()
        assert not any(d.startswith("2016-") for d in dates), (
            "Hong Kong data still has the 2016 year typo"
        )

    def test_myanmar_year_correction(self):
        """The 2011->2021 typo in Myanmar data should be fixed."""
        df = load_timeseries("myanmar_coup_cdm_2021")
        dates = df["date"].tolist()
        assert not any(d.startswith("2011-") for d in dates), (
            "Myanmar data still has the 2011 year typo"
        )

    def test_metadata_embedded(self):
        """Parquet metadata should include case_id and scenario_type."""
        meta = load_timeseries_metadata("brexit_referendum_2016")
        assert "case_id" in meta
        assert "scenario_type" in meta
        assert meta["case_id"] == "brexit_referendum_2016"

    def test_invalid_event_raises(self):
        """Loading a non-existent event should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_timeseries("nonexistent_event")


# ── 4. Sealed splits ────────────────────────────────────────────────────


class TestSealedSplits:
    """Verify split determinism and sealing."""

    def test_splits_file_exists(self):
        assert SPLITS_PATH.exists()

    def test_splits_version(self, splits: dict):
        assert "version" in splits

    def test_splits_seed(self, splits: dict):
        assert splits["seed"] == SPLITS_SEED

    def test_all_events_have_splits(self, splits: dict):
        events = list_timeseries_events()
        for event in events:
            assert event in splits["events"], f"Missing split for: {event}"

    def test_train_split_has_indices(self, splits: dict):
        """Train split should list plaintext indices."""
        for case_id, event_data in splits["events"].items():
            assert "train" in event_data
            assert "indices" in event_data["train"]
            assert len(event_data["train"]["indices"]) > 0

    def test_validation_split_has_indices(self, splits: dict):
        """Validation split should list plaintext indices."""
        for case_id, event_data in splits["events"].items():
            assert "validation" in event_data
            assert "indices" in event_data["validation"]

    def test_historical_test_is_sealed(self, splits: dict):
        """Historical-test should be marked sealed with no plaintext indices."""
        for case_id, event_data in splits["events"].items():
            ht = event_data["historical_test"]
            assert ht.get("sealed") is True, f"{case_id}: historical_test not sealed"
            assert "indices" not in ht, (
                f"{case_id}: historical_test indices leaked in plaintext!"
            )
            assert "hash" in ht
            assert "unlock_required" in ht

    def test_seal_hash_present(self, splits: dict):
        """Overall seal hash should be present."""
        assert "seal" in splits
        assert "seal_hash" in splits["seal"]
        assert len(splits["seal"]["seal_hash"]) == 64

    def test_verify_seal(self):
        """seal_splits() should produce a verifiable seal."""
        seal_splits()
        assert verify_seal() is True

    def test_train_val_accessible_directly(self):
        """Train and validation splits should be accessible via get_split."""
        train = get_split("brexit_referendum_2016", "train")
        assert "indices" in train
        assert "hash" in train

        val = get_split("brexit_referendum_2016", "validation")
        assert "indices" in val
        assert "hash" in val

    def test_historical_test_sealed_without_key(self):
        """Historical-test should raise without an unlock key."""
        with pytest.raises(HistoricalTestSealedError):
            get_split("brexit_referendum_2016", "historical_test")

    def test_historical_test_unlocked_with_correct_key(self):
        """Historical-test should unlock with the correct derived key."""
        key = derive_unlock_key("brexit_referendum_2016")
        result = get_split(
            "brexit_referendum_2016", "historical_test", unlock_key=key
        )
        assert "indices" in result
        assert "hash" in result
        assert len(result["indices"]) > 0

    def test_historical_test_wrong_key_fails(self):
        """An incorrect unlock key should fail."""
        with pytest.raises(HistoricalTestSealedError):
            get_split(
                "brexit_referendum_2016",
                "historical_test",
                unlock_key="wrong_key_12345",
            )

    def test_historical_test_unlocked_indices_are_last_timesteps(self):
        """Historical-test indices should be the last timesteps of the series."""
        key = derive_unlock_key("brexit_referendum_2016")
        result = unlock_historical_test(
            "brexit_referendum_2016", unlock_key=key
        )
        train = get_split("brexit_referendum_2016", "train")
        val = get_split("brexit_referendum_2016", "validation")
        max_train_val_idx = max(train["indices"][-1], val["indices"][-1])
        for idx in result["indices"]:
            assert idx > max_train_val_idx, (
                f"Test index {idx} should be after train/val (max={max_train_val_idx})"
            )
        assert result["n_samples"] == len(result["indices"])

    def test_invalid_split_name_raises(self):
        """An invalid split name should raise ValueError."""
        with pytest.raises(ValueError):
            get_split("brexit_referendum_2016", "invalid_split_name")

    def test_unlock_historical_test_direct_call(self):
        """unlock_historical_test should work directly with correct key."""
        key = derive_unlock_key("brexit_referendum_2016")
        result = unlock_historical_test("brexit_referendum_2016", unlock_key=key)
        assert isinstance(result["indices"], list)

    def test_unlock_historical_test_no_key_raises(self):
        """unlock_historical_test without a key should raise."""
        with pytest.raises(HistoricalTestSealedError):
            unlock_historical_test("brexit_referendum_2016")


# ── 5. Split determinism ────────────────────────────────────────────────


class TestSplitDeterminism:
    """Verify that splits are deterministic given the same seed."""

    def test_same_seed_same_split(self):
        """get_split should return identical results for the same seed."""
        splits1 = get_split("brexit_referendum_2016", "train")
        splits2 = get_split("brexit_referendum_2016", "train")
        assert splits1["indices"] == splits2["indices"]
        assert splits1["hash"] == splits2["hash"]

    def test_hash_unchanged_across_calls(self, splits: dict):
        """Hash locks should remain stable (no random component)."""
        for case_id, event_data in splits["events"].items():
            expected_hash = hashlib.sha256(
                json.dumps(event_data["train"]["indices"], sort_keys=True).encode()
            ).hexdigest()
            assert event_data["train"]["hash"] == expected_hash, (
                f"Train hash mismatch for {case_id}"
            )

    def test_seal_hash_consistency(self, splits: dict):
        """Seal hash should be a valid SHA-256 of the events data."""
        payload = json.dumps(splits["events"], sort_keys=True)
        expected = hashlib.sha256(payload.encode()).hexdigest()
        assert splits["seal"]["seal_hash"] == expected

    def test_unlock_key_deterministic(self):
        """derive_unlock_key should be deterministic."""
        key1 = derive_unlock_key("us_election_2020")
        key2 = derive_unlock_key("us_election_2020")
        assert key1 == key2

    def test_different_cases_different_keys(self):
        """Different case_ids should produce different unlock keys."""
        key1 = derive_unlock_key("brexit_referendum_2016")
        key2 = derive_unlock_key("us_election_2020")
        assert key1 != key2


# ── 6. Provenance ───────────────────────────────────────────────────────


class TestProvenance:
    """Verify the data provenance registry."""

    def test_file_exists(self):
        assert PROVENANCE_PATH.exists()

    def test_registry_structure(self, provenance: dict):
        assert "version" in provenance
        assert "datasets" in provenance

    def test_all_datasets_tracked(self, provenance: dict):
        """Every artefact should appear in provenance."""
        expected = [
            "microdata_synthetic",
            "network_topology",
            "splits",
        ]
        for name in expected:
            assert name in provenance["datasets"], f"Missing provenance for {name}"

        events = list_timeseries_events()
        for event in events:
            key = f"timeseries_{event}"
            assert key in provenance["datasets"], f"Missing provenance for {key}"

    def test_sha256_hashes_present(self, provenance: dict):
        """Every dataset should have a SHA-256 hash."""
        for name, info in provenance["datasets"].items():
            assert "sha256" in info, f"Missing SHA-256 for {name}"
            assert len(info["sha256"]) == 64, f"Invalid SHA-256 length for {name}"

    def test_microdata_hash_verified(self, provenance: dict):
        """Microdata SHA-256 should match the actual file."""
        with open(MICRODATA_PATH, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert provenance["datasets"]["microdata_synthetic"]["sha256"] == actual

    def test_network_hash_verified(self, provenance: dict):
        """Network topology SHA-256 should match the actual file."""
        with open(NETWORK_PATH, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        assert provenance["datasets"]["network_topology"]["sha256"] == actual

    def test_references_present(self, provenance: dict):
        """Provenance should include the academic reference catalogue."""
        assert "references" in provenance
        assert "barabasi_albert_1999" in provenance["references"]
        assert "watts_strogatz_1998" in provenance["references"]
        assert "bakshy_2015" in provenance["references"]
        assert "mcpherson_2001" in provenance["references"]

    def test_historical_test_sealed_in_provenance(self, provenance: dict):
        """Provenance should indicate the historical-test is sealed."""
        splits_info = provenance["datasets"]["splits"]
        assert splits_info.get("historical_test_sealed") is True


# ── 7. Integration: module API smoke test ───────────────────────────────


class TestModuleAPI:
    """Smoke-test the public module API."""

    def test_all_public_symbols_exported(self):
        """All documented public symbols should be importable."""
        import ground_truth as gt
        for name in gt.__all__:
            assert hasattr(gt, name), f"Missing public symbol: {name}"

    def test_load_microdata_returns_dataframe(self):
        df = load_microdata()
        assert isinstance(df, pd.DataFrame)

    def test_load_network_topology_returns_dict(self):
        net = load_network_topology()
        assert isinstance(net, dict)
        assert "degree_distribution" in net

    def test_list_timeseries_events_returns_list(self):
        events = list_timeseries_events()
        assert isinstance(events, list)
        assert len(events) == 12

    def test_seal_splits_idempotent(self):
        """Calling seal_splits twice should produce the same seal."""
        seal_splits()
        with open(SPLITS_PATH) as f:
            hash1 = json.load(f)["seal"]["seal_hash"]

        seal_splits()
        with open(SPLITS_PATH) as f:
            hash2 = json.load(f)["seal"]["seal_hash"]

        assert hash1 == hash2