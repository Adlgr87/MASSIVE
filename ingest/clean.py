import numpy as np
import pandas as pd


def clean_data(df, min_sample_size=100):
    df = df.drop_duplicates()
    for col in df.columns:
        if df[col].dtype in ("float64", "int64"):
            df[col] = df[col].fillna(df[col].median())
        elif df[col].dtype == "object":
            df[col] = df[col].fillna(df[col].mode().iloc[0]) if not df[col].mode().empty else df[col]
    for col in ("support_pct", "oppose_pct", "polarization_index"):
        if col in df.columns:
            lo, hi = df[col].quantile(0.01), df[col].quantile(0.99)
            df[col] = np.clip(df[col], lo, hi)
    if "sample_size" in df.columns:
        df = df[df["sample_size"] >= min_sample_size]
    return df
