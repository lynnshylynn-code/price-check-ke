# ruff: noqa: E501
"""Build the source notebook; execute it with nbconvert before committing."""

import hashlib
import json
from pathlib import Path


def markdown(source: str) -> dict:
    cell_id = hashlib.sha256(source.encode()).hexdigest()[:8]
    return {
        "cell_type": "markdown", "id": cell_id,
        "metadata": {}, "source": source.splitlines(True),
    }


def code(source: str) -> dict:
    cell_id = hashlib.sha256(source.encode()).hexdigest()[:8]
    return {
        "cell_type": "code", "id": cell_id, "execution_count": None, "metadata": {},
        "outputs": [], "source": source.splitlines(True),
    }


cells = [
    markdown("""# Kenya RTFP market prices: CRISP-DM

This notebook studies the World Bank Kenya Monthly Food Price Estimates by Product and Market (RTFP). It is reproducible locally or in Colab. Set `DATA_PATH` to the supplied CSV location. Every numerical result below is computed from that file at execution time; no price observations are fabricated.

## 1. Business understanding

The business questions are: (1) which counties with recorded maize observations have similar mean-price and volatility profiles? (2) based on past county-month observations, is the trailing average currently rising, stable, or falling? (3) what linear trend rate describes each selected county's observed maize series? The last quantity is descriptive and is not a forecast or shopping recommendation.
"""),
    code("""from pathlib import Path
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                             mean_squared_error, r2_score, silhouette_score)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression

# Local path defaults to this repository's dataset; in Colab, upload/mount the CSV
# and set RTFP_CSV to its path before running.
filename = "rtfp_kenya_market_2007_2026-08.csv"
configured_path = os.environ.get("RTFP_CSV")
candidate_paths = ([Path(configured_path)] if configured_path else []) + [
    Path.cwd() / "backend" / "data" / filename,
    Path.cwd().parent / "backend" / "data" / filename,
    Path.cwd() / "data" / filename,
    Path.cwd() / filename,
]
DATA_PATH = next((candidate for candidate in candidate_paths if candidate.exists()), candidate_paths[0])
if not DATA_PATH.exists():
    raise FileNotFoundError(f"Set RTFP_CSV to the supplied dataset; not found: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)
df["price_date"] = pd.to_datetime(df["price_date"], errors="coerce")
print(f"Dataset: {DATA_PATH}")
print(f"Rows: {len(df):,}; columns: {len(df.columns)}")
"""),
    markdown("""## 2. Data understanding

The documented price columns are `beans` and `maize_fao` (KES/kg), and `livestock_goat_s_fao` (KES/unit). `inflation` and fields ending in `price_index` are index measures, not product prices. The source data contains market observations with sparse county/commodity coverage. The inspections below expose that coverage before modeling.
"""),
    code("""display(df.head())
display(df.tail())
df.info()
print("Shape:", df.shape)
display(df.describe(include="object").T)
display(df.isna().sum().sort_values(ascending=False).rename("missing_count").to_frame())

price_columns = ["beans", "maize_fao", "livestock_goat_s_fao"]
for column in price_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")
long_prices = df.melt(
    id_vars=["adm2_name", "mkt_name", "price_date"], value_vars=price_columns,
    var_name="commodity", value_name="price"
).dropna(subset=["price", "price_date"])
long_prices = long_prices[long_prices["mkt_name"].ne("Market Average")]
coverage = (long_prices.groupby(["adm2_name", "commodity"])
            .agg(observations=("price", "size"), first_date=("price_date", "min"),
                 last_date=("price_date", "max")).reset_index())
display(coverage.sort_values(["adm2_name", "commodity"]))
print("Counties with at least one price:", long_prices["adm2_name"].nunique())
"""),
    markdown("""## 3. Data preparation

Missingness is not plausibly MCAR: which data are absent depends on county and commodity coverage and survey availability, so the pattern is at least MAR. Entirely unsurveyed county/commodity combinations (including Kisumu and Nakuru in this file) are also consistent with MNAR/coverage selection: they were not observed by this survey. We drop missing prices for the relevant task rather than impute unobserved markets or imply measured prices. This means all model results describe observed records only.

The IQR rule flags extreme observations for inspection. We report the count and retain flagged values: high and low food prices may be valid economic conditions, and automatic deletion would erase meaningful variation. MinMax scaling is applied to clustering and kNN features because those methods depend on distances. `clean_data.csv` is written outside the repository by default to avoid treating generated artifacts as source data.
"""),
    code("""q1 = long_prices.groupby("commodity")["price"].transform(lambda s: s.quantile(.25))
q3 = long_prices.groupby("commodity")["price"].transform(lambda s: s.quantile(.75))
iqr = q3 - q1
outlier_mask = (long_prices["price"] < q1 - 1.5 * iqr) | (long_prices["price"] > q3 + 1.5 * iqr)
print("IQR flagged rows retained:", int(outlier_mask.sum()), "of", len(long_prices))
clean_data = long_prices.copy()
clean_data["month"] = clean_data["price_date"].dt.to_period("M").dt.to_timestamp()
export_path = Path(os.environ.get("RTFP_CLEAN_EXPORT", "/tmp/rtfp_clean_data.csv"))
clean_data.to_csv(export_path, index=False)
print("Clean data export:", export_path)
"""),
    markdown("""## 4. Modelling

### 4a. Unsupervised county profiles: K-Means

We aggregate observed maize prices to county means and standard deviations to describe profile similarities. This county-month aggregation is an analytical summary only; the API returns observed source-market records and does not average a county. K-Means minimizes squared Euclidean distance, so feature scaling matters. Manhattan distance can be more robust to a single large coordinate difference, but vanilla K-Means optimizes Euclidean squared distance; for Manhattan objectives a medoid-based method would be a better fit.
"""),
    code("""maize = clean_data[clean_data["commodity"].eq("maize_fao")]
county_profile = (maize.groupby("adm2_name")["price"]
                  .agg(mean_price="mean", price_volatility="std", observations="size")
                  .dropna(subset=["mean_price", "price_volatility"]))
profile_features = county_profile[["mean_price", "price_volatility"]]
scaler_cluster = MinMaxScaler()
X_cluster = scaler_cluster.fit_transform(profile_features)
k_values = range(2, min(8, len(profile_features)))
inertias, silhouettes = [], []
for k in k_values:
    model = KMeans(n_clusters=k, random_state=42, n_init=20).fit(X_cluster)
    inertias.append(model.inertia_)
    silhouettes.append(silhouette_score(X_cluster, model.labels_))
best_k = list(k_values)[int(np.argmax(silhouettes))]
cluster_model = KMeans(n_clusters=best_k, random_state=42, n_init=20)
county_profile["cluster"] = cluster_model.fit_predict(X_cluster)
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].plot(list(k_values), inertias, marker="o"); axes[0].set(title="Elbow: inertia", xlabel="k")
axes[1].plot(list(k_values), silhouettes, marker="o"); axes[1].set(title="Silhouette", xlabel="k")
plt.tight_layout(); plt.show()
print("Selected k by maximum silhouette:", best_k)
print("Silhouette at selected k:", round(max(silhouettes), 4))
display(county_profile.sort_values("cluster"))
"""),
    markdown("""### 4b. Supervised county-month trend class

For each county, monthly maize prices are averaged across that month's observed source markets solely for this analysis. We compute a trailing three-month average, then label its change from the preceding trailing average: rising above +2%, falling below −2%, and stable otherwise. The 2% deadband reduces labels driven by tiny month-to-month movement; it is a transparent analytical threshold, not a policy threshold.

Features use only information available before the labeled month: prior monthly price, prior trailing average, and prior one-month percentage change. We use a chronological split so later months are held out; random splitting would leak adjacent time patterns. kNN distance features are MinMax scaled. A decision tree is compared at several depths to show train/test behavior.
"""),
    code("""monthly = (maize.groupby(["adm2_name", "month"], as_index=False)["price"].mean()
           .sort_values(["adm2_name", "month"]))
grouped = monthly.groupby("adm2_name", group_keys=False)
monthly["trailing_mean"] = grouped["price"].transform(lambda s: s.rolling(3, min_periods=3).mean())
monthly["prior_price"] = grouped["price"].shift(1)
monthly["prior_trailing_mean"] = grouped["trailing_mean"].shift(1)
monthly["pct_change"] = grouped["price"].pct_change()
monthly["prior_pct_change"] = monthly.groupby("adm2_name")["pct_change"].shift(1)
monthly["target_change"] = (monthly["trailing_mean"] / grouped["trailing_mean"].shift(1)) - 1
monthly["trend"] = np.select(
    [monthly["target_change"] > .02, monthly["target_change"] < -.02],
    ["rising", "falling"], default="stable"
)
model_data = (monthly.dropna(subset=["prior_price", "prior_trailing_mean", "prior_pct_change", "target_change"])
              .sort_values(["month", "adm2_name"]).copy())
feature_cols = ["prior_price", "prior_trailing_mean", "prior_pct_change"]
unique_months = sorted(model_data["month"].unique())
split_month = unique_months[int(len(unique_months) * .8)]
train, test = model_data[model_data["month"] < split_month], model_data[model_data["month"] >= split_month]
X_train, X_test = train[feature_cols], test[feature_cols]
y_train, y_test = train["trend"], test["trend"]
print("Chronological train rows:", len(train), "test rows:", len(test))
print("Train last month:", train["month"].max(), "test first month:", test["month"].min())
"""),
    code("""knn_scaler = MinMaxScaler()
X_train_scaled = knn_scaler.fit_transform(X_train)
X_test_scaled = knn_scaler.transform(X_test)
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train_scaled, y_train)
knn_pred = knn.predict(X_test_scaled)
print("kNN train accuracy:", round(accuracy_score(y_train, knn.predict(X_train_scaled)), 4))
print("kNN test accuracy:", round(accuracy_score(y_test, knn_pred), 4))
print("kNN confusion matrix (labels falling, stable, rising):")
print(confusion_matrix(y_test, knn_pred, labels=["falling", "stable", "rising"]))
print(classification_report(y_test, knn_pred, labels=["falling", "stable", "rising"], zero_division=0))

tree_results = []
for depth in [2, 4, 8, None]:
    tree = DecisionTreeClassifier(max_depth=depth, random_state=42, class_weight="balanced")
    tree.fit(X_train, y_train)
    tree_results.append({"max_depth": str(depth),
                         "train_accuracy": accuracy_score(y_train, tree.predict(X_train)),
                         "test_accuracy": accuracy_score(y_test, tree.predict(X_test))})
tree_results = pd.DataFrame(tree_results)
display(tree_results)
best_depth = tree_results.iloc[tree_results["test_accuracy"].argmax()]["max_depth"]
chosen_depth = None if best_depth == "None" else int(best_depth)
tree = DecisionTreeClassifier(max_depth=chosen_depth, random_state=42, class_weight="balanced")
tree.fit(X_train, y_train)
tree_pred = tree.predict(X_test)
print("Selected max_depth by held-out accuracy:", best_depth)
print("Decision tree confusion matrix (labels falling, stable, rising):")
print(confusion_matrix(y_test, tree_pred, labels=["falling", "stable", "rising"]))
print(classification_report(y_test, tree_pred, labels=["falling", "stable", "rising"], zero_division=0))
"""),
    markdown("""### 4c. Regression trend lines

For up to five counties with the most maize observations, fit a linear regression of price on elapsed month index. The slope is a descriptive KES/kg per month trend over observed values. It does not account for seasonality or future shocks and must not be presented as a forecast.
"""),
    code("""regression_rows = []
selected_counties = maize.groupby("adm2_name").size().nlargest(5).index
for county in selected_counties:
    series = (maize[maize["adm2_name"].eq(county)].groupby("month", as_index=False)["price"].mean()
              .sort_values("month"))
    time_index = np.arange(len(series)).reshape(-1, 1)
    model = LinearRegression().fit(time_index, series["price"])
    predicted = model.predict(time_index)
    rmse = mean_squared_error(series["price"], predicted) ** .5
    regression_rows.append({"county": county, "observations": len(series),
                            "slope_KES_per_kg_per_month": model.coef_[0],
                            "R2_descriptive": r2_score(series["price"], predicted), "RMSE": rmse})
display(pd.DataFrame(regression_rows).round(4))
"""),
    markdown("""## 5. Evaluation

The notebook prints confusion matrices and per-class precision, recall, and F1 for both classifiers. It compares training and chronological test accuracy across tree depths; a large gap indicates overfitting. Regression reports in-sample descriptive R² and RMSE, which are not predictive validation scores. Clustering quality is reported with silhouette as well as the elbow curve. These metrics apply only to the dataset's observed coverage, not to unsurveyed counties.
"""),
    markdown("""## 6. Deployment

A future API could optionally expose a county's descriptive cluster label alongside the exact observations, model version, training data coverage, and a clear explanation that county profiles summarize observed source markets. The service should retain missing-data states, monitor coverage and model drift, and avoid showing a cluster when the county has insufficient observations. Trend classes and regression slopes should remain historical summaries. This project does not claim representative coverage of Kenya, causal explanations, future prices, supermarket prices, or purchase advice.
"""),
]

notebook = {
    "cells": cells,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                 "language_info": {"name": "python", "version": "3.11+"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}
destination = Path(__file__).resolve().parents[2] / "notebooks" / "rtfp_crisp_dm.ipynb"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print(destination)
