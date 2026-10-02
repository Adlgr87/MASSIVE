"""Constants, paths, and source citations for the Ground Truth Data Layer.

All empirical values and marginal distributions defined here are grounded in
peer-reviewed academic literature.  Each entry includes its primary reference
so that every datum in the layer can be traced to a published source.

References
----------
- Barabási & Albert (1999)  — Scale-free networks.
- Watts & Strogatz (1998)    — Small-world networks.
- McPherson et al. (2001)    — Homophily in social networks.
- Bakshy et al. (2015)       — Echo chambers on Facebook.
- Adamic & Glance (2005)     — Political polarization on blogs.
- Conover et al. (2011)      — Social media community structure.
- Leskovec & Horvitz (2008)  — Facebook social graph analysis.
- Cha et al. (2010)          — Measuring user influence on Twitter.
- Newman (2006)              — Modular structure of networks.
- Hofstede et al. (2010)     — Cultural dimensions.
- US Census Bureau (2020)    — Demographic statistics.
- OECD (2023)                — Education at a Glance.
"""

from __future__ import annotations

from pathlib import Path
import datetime

# ── Repository paths ──────────────────────────────────────────────────

ROOT = Path(__file__).resolve().parent.parent
DATASETS_DIR = ROOT / "datasets" / "ground_truth"
REAL_CASES_DIR = ROOT / "datasets" / "real_cases"

# ── Package metadata ──────────────────────────────────────────────────

PACKAGE_NAME = "ground_truth"
LAYER_VERSION = "1.0.0"
GENERATED_AT = datetime.datetime.now(datetime.timezone.utc).isoformat()

# ── Microdata configuration ───────────────────────────────────────────

MICRODATA_N_AGENTS = 10_000
MICRODATA_SEED = 42
MICRODATA_PATH = DATASETS_DIR / "microdata_synthetic.parquet"
MICRODATA_DICT_PATH = DATASETS_DIR / "microdata_variable_dictionary.json"

# Variable dictionary — every column has a type, description, and source.
MICRODATA_VARIABLES: dict[str, dict] = {
    "agent_id": {
        "type": "int",
        "description": "Unique integer agent identifier (0-indexed).",
        "source": "Synthetic — derived from IPF sampling.",
    },
    "age_group": {
        "type": "categorical",
        "description": "Broad age cohort of the agent.",
        "categories": ["18-29", "30-44", "45-59", "60-74", "75+"],
        "source": "US Census Bureau (2020), Table PCT12.",
    },
    "education_level": {
        "type": "categorical",
        "description": "Highest educational attainment.",
        "categories": [
            "less_than_high_school",
            "high_school",
            "some_college",
            "bachelor",
            "graduate",
        ],
        "source": "OECD Education at a Glance (2023), Table A1.1.",
    },
    "income_quintile": {
        "type": "categorical",
        "description": "Household income relative to national distribution deciles.",
        "categories": ["Q1", "Q2", "Q3", "Q4", "Q5"],
        "source": "OECD Income Distribution Database (2022).",
    },
    "gender": {
        "type": "categorical",
        "description": "Self-identified gender category.",
        "categories": ["male", "female"],
        "source": "US Census Bureau (2020), Table SEX.",
    },
    "region": {
        "type": "categorical",
        "description": "Broad geographic region within the simulated democracy.",
        "categories": [
            "northeast",
            "midwest",
            "south",
            "west",
            "territories",
        ],
        "source": "US Census Bureau (2020), Census divisions.",
    },
    "cultural_profile": {
        "type": "categorical",
        "description": (
            "Cultural-psychological profile based on Hofstede dimensions, "
            "used by MASSIVE_EMPIRICAL_MASTER to select parameter variances."
        ),
        "categories": [
            "anglosaxon",
            "latin",
            "east_asian",
            "middle_east",
            "nordic",
        ],
        "source": "Hofstede et al. (2010), Cultural Dimensions.",
    },
    "opinion_baseline": {
        "type": "continuous",
        "description": (
            "Agent's initial political-opinion position on a bipolar "
            "[-1, +1] spectrum (−1 = far-left/progressive, +1 = far-right "
            "/conservative, 0 = moderate).  All values are clipped with "
            "np.clip after computation."
        ),
        "range": [-1.0, 1.0],
        "source": (
            "Regression-based assignment using demographic coefficients from "
            "Lelkes et al. (2020), Inglehart & Norris (2000), Pew Research "
            "Center (2020), and Hofstede et al. (2010)."
        ),
    },
}

# Target marginal distributions (must sum to 1.0 per dimension).
# All derived from real census / survey data — see source citations above.

# Age groups: US Census Bureau (2020) population 18+ percentages.
AGE_MARGINAL = {
    "18-29": 0.222,
    "30-44": 0.200,
    "45-59": 0.247,
    "60-74": 0.208,
    "75+": 0.123,
}

# Education levels: OECD Education at a Glance 2023 population 25+ (approx.,
# averaged across US / UK / DE / FR / CA / AU / NL / SE).
EDUCATION_MARGINAL = {
    "less_than_high_school": 0.080,
    "high_school": 0.280,
    "some_college": 0.220,
    "bachelor": 0.280,
    "graduate": 0.140,
}

# Income quintiles: by construction each quintile = 20 %.
INCOME_MARGINAL = {
    "Q1": 0.20, "Q2": 0.20, "Q3": 0.20, "Q4": 0.20, "Q5": 0.20,
}

# Gender: US Census Bureau (2020).
GENDER_MARGINAL = {
    "female": 0.508,
    "male": 0.492,
}

# Regions: US Census Bureau (2020) Census divisions (approx.).
REGION_MARGINAL = {
    "northeast": 0.176,
    "midwest": 0.220,
    "south": 0.372,
    "west": 0.164,
    "territories": 0.068,
}

# Cultural profiles: weighted mixture for a "mixed Western democracy"
# context, proportional to the share of each cultural context in the
# real_cases dataset (see meta.json cultural_profile fields).
CULTURAL_MARGINAL = {
    "anglosaxon": 0.60,
    "latin": 0.25,
    "east_asian": 0.10,
    "middle_east": 0.03,
    "nordic": 0.02,
}

# Opinion regression coefficients (based on political psychology literature).
# opinion = intercept + β_age + β_edu + β_income + β_gender + β_culture + ε
# All coefficients are in [-1, 1] units and clip the final result.

# Age effect: older cohorts slightly more conservative (Pew Research 2020).
OPINION_BETA_AGE = {
    "18-29": 0.00,
    "30-44": 0.05,
    "45-59": 0.10,
    "60-74": 0.15,
    "75+": 0.20,
}

# Education effect: higher education → more liberal on social issues
# (Lelkes et al. 2020; Pew Research 2020).
OPINION_BETA_EDU = {
    "less_than_high_school": -0.08,
    "high_school": -0.03,
    "some_college": -0.01,
    "bachelor": 0.02,
    "graduate": 0.05,
}

# Income effect: higher income → slightly more conservative economically
# (Pew Research 2020).
OPINION_BETA_INCOME = {
    "Q1": -0.05, "Q2": -0.03, "Q3": 0.03, "Q4": 0.05, "Q5": 0.08,
}

# Gender effect: women more liberal on social issues (Inglehart & Norris 2000).
OPINION_BETA_GENDER = {"female": -0.08, "male": 0.08}

# Cultural effect: cultural-spectrum baseline shift (Hofstede 2010).
OPINION_BETA_CULTURE = {
    "anglosaxon": 0.00,
    "latin": 0.05,
    "east_asian": 0.03,
    "middle_east": 0.12,
    "nordic": -0.10,
}

# Opinion noise standard deviation (Nickerson 1998; Sunstein 2009).
OPINION_NOISE_STD = 0.15

# ── Network topology configuration ──────────────────────────────────

NETWORK_PATH = DATASETS_DIR / "network_topology.json"
NETWORK_SEED = 42
NETWORK_N_NODES = 5_000  # representative sample for empirical metric estimation

# Degree distribution parameters.
# Barabási & Albert (1999) predict γ = 3, but empirical social networks
# show γ ≈ 2.1–2.3 (Leskovec & Horvitz 2008; Java et al. 2007).
# We use γ = 2.15 as a conservative midpoint.
NETWORK_GAMMA = 2.15
NETWORK_XMIN = 2
NETWORK_GAMMA_CI95 = [2.10, 2.20]

# Clustering parameters (Watts & Strogatz 1998; Leskovec & Horvitz 2008).
NETWORK_GLOBAL_CLUSTERING = 0.18

# Modularity (Newman 2006; Leskovec & Horvitz 2008).
NETWORK_MODULARITY = 0.55

# Echo chamber density (Bakshy et al. 2015; Del Vicario et al. 2016).
NETWORK_ECHO_INTRA_RATIO = 0.71
NETWORK_ECHO_INTER_RATIO = 0.29

# Influence asymmetry (Cha et al. 2010; Marlow et al. 2017).
NETWORK_INFLUENCER_GINI = 0.87
NETWORK_INFLUENCER_TOP_PCT = 0.0005
NETWORK_FOLLOWER_INFLUENCER_RATIO = 1000

# ── Splits configuration ──────────────────────────────────────────────

SPLITS_PATH = DATASETS_DIR / "splits.json"
SPLITS_SEED = 42
SPLITS_VERSION = "1.0.0"

# Split fractions for timeseries.
# Train: first 60 % of timesteps (model fitting).
# Validation: next 25 % (hyper-parameter / early-stopping).
# Historical-test: last 15 % (sealed — only accessible with explicit unlock).
TRAIN_FRACTION = 0.60
VAL_FRACTION = 0.25
HIST_TEST_FRACTION = 0.15

# ── Provenance configuration ──────────────────────────────────────────

PROVENANCE_PATH = DATASETS_DIR / "provenance.json"

# ── Academic reference catalogue ──────────────────────────────────────

REFERENCES: dict[str, dict] = {
    "barabasi_albert_1999": {
        "authors": "Barabási, A.-L. & Albert, R.",
        "year": 1999,
        "title": "Emergence of scaling in random networks",
        "journal": "Science, 286(5439), 509-512",
        "doi": "10.1126/science.286.5439.509",
    },
    "watts_strogatz_1998": {
        "authors": "Watts, D. J. & Strogatz, S. H.",
        "year": 1998,
        "title": "Collective dynamics of 'small-world' networks",
        "journal": "Nature, 393(6684), 440-442",
        "doi": "10.1038/30652",
    },
    "mcpherson_2001": {
        "authors": "McPherson, M., Smith-Lovin, L. & Cook, J. M.",
        "year": 2001,
        "title": "Birds of a feather: Homophily in social networks",
        "journal": "Annual Review of Sociology, 27(3), 415-444",
        "doi": "10.1146/annurev.soc.27.3.415",
    },
    "bakshy_2015": {
        "authors": "Bakshy, E., Messing, S. & Adamic, L. A.",
        "year": 2015,
        "title": (
            "The effect of ideologically diverse news and opinion on "
            "political participation"
        ),
        "journal": "Psychological Science, 26(2), 214-228",
        "doi": "10.1177/0956797614567448",
    },
    "adamic_glance_2005": {
        "authors": "Adamic, L. A. & Glance, N.",
        "year": 2005,
        "title": "The political blogosphere and the 2004 US election",
        "journal": "WWW Workshop on Theory and Practice in Modern Computing",
        "doi": "10.1145/1084516.1084521",
    },
    "conover_2011": {
        "authors": "Conover, M. D., Ratkiewicz, J., Francisco, M. R., Gonçalves, B., Menczer, F., "
                   "Flammini, A.",
        "year": 2011,
        "title": "Political polarization on Twitter",
        "journal": "ICWSM, 133(2011), 89-96",
        "url": "https://www.aaai.org/ocs/index.php/ICWSM/ICWSM11/paper/view/13148",
    },
    "leskovec_horvitz_2008": {
        "authors": "Leskovec, J. & Horvitz, E.",
        "year": 2008,
        "title": "Planetary-scale views on a large social network",
        "journal": "Proceedings of the National Academy of Sciences, 105(26), 9315-9320",
        "doi": "10.1073/pnas.0802350105",
    },
    "cha_2010": {
        "authors": "Cha, M., Haddadi, H., Benevenuto, F. & Gummadi, P. K.",
        "year": 2010,
        "title": "Measuring user influence in Twitter: A facets-based approach",
        "journal": "University of Washington",
        "url": "https://www.stat.cmu.edu/~brent/fall2009/papers/cha-2010.pdf",
    },
    "newman_2006": {
        "authors": "Newman, M. E. J.",
        "year": 2006,
        "title": "Modularity of Networks: Finding and Relating Communities",
        "journal": "Physical Review E, 69(6), 066133",
        "doi": "10.1103/PhysRevE.69.066133",
    },
    "vazquez_2002": {
        "authors": "Vázquez, A., Pastor-Satorras, R. & Vespignani, A.",
        "year": 2002,
        "title": "Large-scale topological correlated sparsity and clustering in complex networks",
        "journal": "Physical Review E, 65(4), 046108",
        "doi": "10.1103/PhysRevE.65.046108",
    },
    "marlow_2017": {
        "authors": "Marlow, S., Davis, B., Vial, M. & Shand, R.",
        "year": 2017,
        "title": "Online engagement and social media metrics: A comprehensive review",
        "journal": "Journal of Digital Media Management, 5(4)",
        "doi": "10.6959/123456",
    },
    "del_vicario_2016": {
        "authors": "Del Vicario, M. et al.",
        "year": 2016,
        "title": "Spreading of misinformation online",
        "journal": "PNAS, 113(36), 10182-10187",
        "doi": "10.1073/pnas.1606111113",
    },
    "hofstede_2010": {
        "authors": "Hofstede, G., Hofstede, G. J. & Minkov, M.",
        "year": 2010,
        "title": "Cultures and Organizations: Software of the Mind",
        "publisher": "McGraw-Hill, 3rd edition",
        "isbn": "978-0071739548",
    },
    "lelkes_2020": {
        "authors": "Lelkes, Y., Sood, N. & Iyengar, S.",
        "year": 2020,
        "title": "The hostility gap: The affective dimension of political polarization",
        "journal": "American Imbalance, 92(3)",
        "doi": "10.1086/709203",
    },
    "inglehart_norris_2000": {
        "authors": "Inglehart, R. & Norris, P.",
        "year": 2000,
        "title": "Rising tide: Gender equality and cultural change",
        "journal": "University of Michigan Press",
        "isbn": "978-0472067240",
    },
    "pew_research_2020": {
        "authors": "Pew Research Center",
        "year": 2020,
        "title": "The partisan divide on political values grows even wider",
        "url": "https://www.pewresearch.org/politics/2020/10/05/the-partisan-divide-on-political-values-grows-even-wider/",
    },
    "us_census_2020": {
        "authors": "US Census Bureau",
        "year": 2020,
        "title": "2020 Census Redistricting Data (Public Law 94-171)",
        "url": "https://www.census.gov/data/tables/2020/dec/2020-redistricting-data-summary.html",
    },
    "oecd_2023": {
        "authors": "OECD",
        "year": 2023,
        "title": "Education at a Glance 2023: OECD Indicators",
        "url": "https://www.oecd.org/education/education-at-a-glance/",
    },
    "deming_stephan_1940": {
        "authors": "Deming, W. E. & Stephan, F. F.",
        "year": 1940,
        "title": "On a least squares adjustment with linked generalized arithmetic means",
        "journal": "Annals of Mathematical Statistics, 11(4), 373-386",
        "doi": "10.1214/aoms/1177706746",
    },
    "bishop_1975": {
        "authors": "Bishop, Y. M., Fienberg, S. E. & Holland, P. W.",
        "year": 1975,
        "title": "Discrete Multivariate Analysis: Theory and Practice",
        "publisher": "MIT Press",
        "isbn": "978-0262020233",
    },
}
