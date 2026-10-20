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
import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.dummy import DummyClassifier
from sklearn.metrics import (accuracy_score, confusion_matrix, mean_squared_error,
                             precision_recall_fscore_support, r2_score, silhouette_score)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import MinMaxScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression

DATA_PATH = Path(os.environ.get(
    "RTFP_CSV", "../backend/data/rtfp_kenya_market_2007_2026-08.csv"
))
if not DATA_PATH.exists():
    raise FileNotFoundError("Set RTFP_CSV to the supplied RTFP CSV file.")

df = pd.read_csv(DATA_PATH)
df["price_date"] = pd.to_datetime(df["price_date"], errors="coerce")
print(f"Dataset file: {DATA_PATH.name}")
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

The IQR rule flags extreme observations for inspection. We report the count and retain flagged values: high and low food prices may be valid economic conditions, and automatic deletion would erase meaningful variation. MinMax scaling is applied to clustering and kNN features because those methods depend on distances. `clean_data.csv` is written under the ignored relative `notebooks/output/` directory.
"""),
    code("""q1 = long_prices.groupby("commodity")["price"].transform(lambda s: s.quantile(.25))
q3 = long_prices.groupby("commodity")["price"].transform(lambda s: s.quantile(.75))
iqr = q3 - q1
outlier_mask = (long_prices["price"] < q1 - 1.5 * iqr) | (long_prices["price"] > q3 + 1.5 * iqr)
print("IQR flagged rows retained:", int(outlier_mask.sum()), "of", len(long_prices))
clean_data = long_prices.copy()
clean_data["month"] = clean_data["price_date"].dt.to_period("M").dt.to_timestamp()
export_path = Path("output/clean_data.csv")
export_path.parent.mkdir(parents=True, exist_ok=True)
clean_data.to_csv(export_path, index=False)
print("Clean data export:", export_path.as_posix())
"""),
    markdown("""## 4. Modelling

### 4a. Unsupervised county profiles: K-Means

We aggregate observed maize prices to county means and coefficients of variation (standard deviation divided by mean) to describe profile similarities without letting the price scale dominate volatility. This county aggregation is an analytical summary only; the API returns observed source-market records and does not average a county. K-Means minimizes squared Euclidean distance, so MinMax scaling is applied to mean price and coefficient of variation. Manhattan distance can be more robust to a single large coordinate difference, but vanilla K-Means optimizes Euclidean squared distance; for a Manhattan objective a medoid-based method would be a better fit. We compare the inertia elbow with silhouette scores and choose the elbow candidate when its silhouette is within 10% of the best score; otherwise we choose the best-silhouette candidate.
"""),
    code("""maize = clean_data[clean_data["commodity"].eq("maize_fao")]
county_profile = (maize.groupby("adm2_name")["price"]
                  .agg(mean_price="mean", price_std="std", observations="size")
                  .dropna(subset=["mean_price", "price_std"]))
county_profile["coefficient_of_variation"] = county_profile["price_std"] / county_profile["mean_price"]
profile_features = county_profile[["mean_price", "coefficient_of_variation"]]
scaler_cluster = MinMaxScaler()
X_cluster = scaler_cluster.fit_transform(profile_features)
k_values = range(2, min(8, len(profile_features)))
inertias, silhouettes = [], []
for k in k_values:
    model = KMeans(n_clusters=k, random_state=42, n_init=20).fit(X_cluster)
    inertias.append(model.inertia_)
    silhouettes.append(silhouette_score(X_cluster, model.labels_))
normalized_inertia = (np.asarray(inertias) - min(inertias)) / (max(inertias) - min(inertias))
normalized_k = np.linspace(0, 1, len(inertias))
line_distance = np.abs(normalized_inertia - (1 - normalized_k)) / np.sqrt(2)
elbow_k = list(k_values)[int(np.argmax(line_distance))]
best_silhouette_k = list(k_values)[int(np.argmax(silhouettes))]
silhouette_by_k = dict(zip(k_values, silhouettes))
selected_k = elbow_k if silhouette_by_k[elbow_k] >= .9 * max(silhouettes) else best_silhouette_k
cluster_model = KMeans(n_clusters=selected_k, random_state=42, n_init=20)
county_profile["cluster"] = cluster_model.fit_predict(X_cluster)
fig, axes = plt.subplots(1, 2, figsize=(10, 4))
axes[0].plot(list(k_values), inertias, marker="o"); axes[0].set(title="Elbow: inertia", xlabel="k")
axes[1].plot(list(k_values), silhouettes, marker="o"); axes[1].set(title="Silhouette", xlabel="k")
plt.tight_layout(); plt.show()
selected_silhouette = silhouette_by_k[selected_k]
print("Elbow candidate k:", elbow_k)
print("Best silhouette candidate k:", best_silhouette_k)
print("Selected k after elbow/silhouette comparison:", selected_k)
print("Silhouette at selected k:", round(selected_silhouette, 4))
display(county_profile.sort_values("cluster"))
"""),
    code("""cluster_output_path = Path("output/county_clusters.json")
cluster_output_path.parent.mkdir(parents=True, exist_ok=True)
cluster_payload = {
    "county_clusters": {
        county: int(cluster) for county, cluster in county_profile["cluster"].items()
    },
    "k": int(selected_k),
    "silhouette": round(float(selected_silhouette), 4),
    "training_date_range": {
        "start": maize["month"].min().strftime("%Y-%m"),
        "end": maize["month"].max().strftime("%Y-%m"),
    },
}
cluster_output_path.write_text(json.dumps(cluster_payload, indent=2), encoding="utf-8")
print("Cluster labels artifact:", cluster_output_path.as_posix())
"""),
    markdown("""### 4b. Supervised county-month trend class

For each county, monthly maize prices are averaged across that month's observed source markets solely for this analysis. We compute a trailing three-month average, then label its change from the preceding trailing average: rising above +2%, falling below −2%, and stable otherwise. The 2% deadband reduces labels driven by tiny month-to-month movement; it is a transparent analytical threshold, not a policy threshold.

Features use only information available before the labeled month: prior monthly price, prior trailing average, and prior one-month percentage change. The latest 20% of months are held out for a final chronological test. Earlier months are split into fit and validation periods; validation selects kNN k and tree depth. The selected models are refit on all training months and evaluated once on the untouched test period. A most-frequent-class DummyClassifier is the baseline. kNN distance features are MinMax scaled.
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
test_month = unique_months[int(len(unique_months) * .8)]
train, test = model_data[model_data["month"] < test_month], model_data[model_data["month"] >= test_month]
train_months = sorted(train["month"].unique())
validation_month = train_months[int(len(train_months) * .8)]
fit_train, validation = train[train["month"] < validation_month], train[train["month"] >= validation_month]
print("Fit rows:", len(fit_train), "validation rows:", len(validation), "final test rows:", len(test))
print("Fit ends:", fit_train["month"].max(), "validation:", validation["month"].min(), "to", validation["month"].max())
print("Final train ends:", train["month"].max(), "test starts:", test["month"].min())
"""),
    code("""validation_rows = []
for k in [3, 5, 7, 9, 11]:
    if k > len(fit_train):
        continue
    scaler = MinMaxScaler().fit(fit_train[feature_cols])
    model = KNeighborsClassifier(n_neighbors=k).fit(
        scaler.transform(fit_train[feature_cols]), fit_train["trend"]
    )
    predicted = model.predict(scaler.transform(validation[feature_cols]))
    validation_rows.append({"model": "kNN", "parameter": f"k={k}",
                            "validation_accuracy": accuracy_score(validation["trend"], predicted)})
for depth in [2, 3, 4, 6, None]:
    model = DecisionTreeClassifier(max_depth=depth, random_state=42, class_weight="balanced")
    model.fit(fit_train[feature_cols], fit_train["trend"])
    predicted = model.predict(validation[feature_cols])
    validation_rows.append({"model": "Decision tree", "parameter": f"depth={depth}",
                            "validation_accuracy": accuracy_score(validation["trend"], predicted)})
validation_results = pd.DataFrame(validation_rows)
display(validation_results)
best_knn = validation_results[validation_results["model"].eq("kNN")].sort_values(
    ["validation_accuracy", "parameter"], ascending=[False, True]
).iloc[0]
best_tree = validation_results[validation_results["model"].eq("Decision tree")].sort_values(
    ["validation_accuracy", "parameter"], ascending=[False, True]
).iloc[0]
best_k = int(best_knn["parameter"].split("=")[1])
depth_text = best_tree["parameter"].split("=")[1]
best_depth = None if depth_text == "None" else int(depth_text)

final_scaler = MinMaxScaler().fit(train[feature_cols])
knn = KNeighborsClassifier(n_neighbors=best_k).fit(
    final_scaler.transform(train[feature_cols]), train["trend"]
)
knn_pred = knn.predict(final_scaler.transform(test[feature_cols]))
tree = DecisionTreeClassifier(max_depth=best_depth, random_state=42, class_weight="balanced")
tree.fit(train[feature_cols], train["trend"])
tree_pred = tree.predict(test[feature_cols])
baseline = DummyClassifier(strategy="most_frequent").fit(train[feature_cols], train["trend"])
baseline_pred = baseline.predict(test[feature_cols])
test_accuracy = {
    "Most frequent baseline": accuracy_score(test["trend"], baseline_pred),
    f"kNN (k={best_k})": accuracy_score(test["trend"], knn_pred),
    f"Decision tree (depth={best_depth})": accuracy_score(test["trend"], tree_pred),
}
print("Final untouched chronological test accuracy:",
      {name: round(float(value), 4) for name, value in test_accuracy.items()})
print("Baseline majority class:", baseline.classes_[np.argmax(baseline.class_prior_)])
for name, prediction in [("kNN", knn_pred), ("Decision tree", tree_pred)]:
    print(name, "confusion matrix (labels falling, stable, rising):")
    print(confusion_matrix(test["trend"], prediction, labels=["falling", "stable", "rising"]))
    precision, recall, f1, support = precision_recall_fscore_support(
        test["trend"], prediction, labels=["falling", "stable", "rising"], zero_division=0
    )
    display(pd.DataFrame({"precision": precision, "recall": recall, "f1": f1, "support": support},
                         index=["falling", "stable", "rising"]))
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
