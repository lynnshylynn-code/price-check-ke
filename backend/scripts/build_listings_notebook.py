# ruff: noqa: E501
"""Generate the reproducible listings CRISP-DM notebook."""

import hashlib
import json
import textwrap
from pathlib import Path


def markdown(source: str, index: int) -> dict:
    return {
        "cell_type": "markdown",
        "id": f"listing-md-{index}-{hashlib.sha1(source.encode()).hexdigest()[:6]}",
        "metadata": {},
        "source": source.splitlines(True),
    }


def code(source: str, index: int) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "id": f"listing-code-{index}-{hashlib.sha1(source.encode()).hexdigest()[:6]}",
        "metadata": {},
        "outputs": [],
        "source": textwrap.dedent(source).splitlines(True),
    }


cells = [
    markdown("""# Kenya supermarket listings: CRISP-DM

Reproducible analysis of the supplied advertised listing snapshot. Run from the repository root or set `LISTINGS_CSV`. The optional APHRC workbook is read only from `backend/data/listings/private/`; it has no prices and remains ignored by Git. No human `label` values are inferred from the separate suggestion columns.

## 1. Business understanding

Study snapshot coverage and unit prices, evaluate product wording models trained on the optional APHRC catalogue, and assess candidate matching. The output is not sales, stock, checkout, or price-history data and is not a deployment claim.
""", 0),
    markdown("## 2. Data understanding\n", 1),
    code("""
        from pathlib import Path
        import os, re, json, sys
        import numpy as np
        import pandas as pd
        from sklearn.dummy import DummyClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,
                                     f1_score, precision_recall_fscore_support)
        from sklearn.model_selection import GroupShuffleSplit, train_test_split
        from sklearn.naive_bayes import MultinomialNB
        from sklearn.pipeline import make_pipeline
        from sklearn.tree import DecisionTreeClassifier

        ROOT = Path.cwd()
        if not (ROOT / 'backend').is_dir(): ROOT = ROOT.parent
        sys.path.insert(0, str(ROOT / 'backend/src'))
        DATA = Path(os.environ.get('LISTINGS_CSV', ROOT / 'backend/data/listings/kenya_supermarket_public_listings.csv'))
        df = pd.read_csv(DATA)
        print('Dataset file:', DATA.name, '| shape:', df.shape)
        display(df.dtypes.rename('dtype').to_frame())
        display(df.isna().sum().rename('missing').to_frame())
        display(df.groupby('supermarket').size().rename('rows').to_frame())
        prices = pd.to_numeric(df.price_kes, errors='coerce').dropna()
        display(prices.describe(percentiles=[.1,.25,.5,.75,.9,.95]).to_frame('price_kes'))
        q1,q3=prices.quantile(.25),prices.quantile(.75); iqr=q3-q1
        outliers=(prices<q1-1.5*iqr)|(prices>q3+1.5*iqr)
        print('Price IQR outliers:', int(outliers.sum()), 'of', len(prices))
    """, 2),
    markdown("""## 3. Data preparation

Blank `pack_size` values remain missing because their sizes are unknown. Unit price uses the API's conservative UOM plus regex parser and remains null for ambiguous multipacks. IQR outliers are flagged for inspection, not deleted. Log transform is used only for price distribution analysis. The discount summary is descriptive and subject to homepage-offer selection bias.
""", 3),
    code("""
        from price_check_api.listings import get_listings
        listings = get_listings()
        df['price_kes'] = pd.to_numeric(df.price_kes, errors='coerce')
        df['log_price'] = np.log1p(df.price_kes)
        regular = pd.to_numeric(df.regular_price_kes, errors='coerce')
        discount = (regular - df.price_kes) / regular
        print('Rows with regular prices:', int(regular.notna().sum()))
        print('Mean displayed discount:', round(float(discount.dropna().mean()), 4))
        unit_df = pd.DataFrame([{'store':x.supermarket,'category':x.category,'unit':x.unit,
                                 'unit_price':x.unit_price} for x in listings if x.unit_price is not None])
        if not unit_df.empty:
            display(unit_df.groupby(['category','unit','store']).unit_price.agg(['count','median','min','max']))
            q1=unit_df.groupby(['category','unit']).unit_price.transform(lambda s:s.quantile(.25))
            q3=unit_df.groupby(['category','unit']).unit_price.transform(lambda s:s.quantile(.75))
            iqr=q3-q1
            print('Comparable-unit IQR outliers:', int(((unit_df.unit_price<q1-1.5*iqr)|(unit_df.unit_price>q3+1.5*iqr)).sum()))
        print('Offer-skew caveat: the snapshot favors advertised offers and is not a representative price history.')
    """, 4),
    markdown("""## 4. Modelling

### 4a. APHRC food-group and NOVA classification

Each target uses the same grouped holdout split by normalized description to reduce near-duplicate leakage. Report a majority DummyClassifier, TF-IDF plus MultinomialNB, and TF-IDF plus decision tree. Per-class precision, recall, F1, and confusion matrices are printed. The final APHRC models are then refit on all labelled catalogue rows for snapshot inference; these saved models are not retailer-validated.
""", 5),
    code("""
        from pathlib import Path
        from sklearn.base import clone
        import joblib

        APHRC = ROOT / 'backend/data/listings/private/APHRC_supermarket_item_catalogue_and_dictionary.xlsx'
        OUTPUT = ROOT / 'notebooks/output'
        OUTPUT.mkdir(parents=True, exist_ok=True)
        trained_models = {}
        if not APHRC.exists():
            print('Skipped APHRC classification: optional workbook not present.')
        else:
            catalogue = pd.read_excel(APHRC, sheet_name='unique_items')
            catalogue['description'] = catalogue.description.fillna('').astype(str)
            catalogue['_group'] = (catalogue.description.str.casefold()
                                   .str.replace(r'[^a-z0-9]+',' ',regex=True).str.strip())
            for target in ['food_group','nova']:
                train_data=catalogue[catalogue[target].notna() & catalogue._group.ne('')].copy()
                y=train_data[target].astype(str)
                splitter=GroupShuffleSplit(n_splits=1,test_size=.2,random_state=42)
                tr,te=next(splitter.split(train_data.description,y,groups=train_data._group))
                estimators={
                    'Dummy majority':DummyClassifier(strategy='most_frequent'),
                    'MultinomialNB':make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=2),MultinomialNB()),
                    'DecisionTree':make_pipeline(TfidfVectorizer(ngram_range=(1,2),min_df=2),DecisionTreeClassifier(max_depth=30,random_state=42)),
                }
                print('\\nTARGET:',target,'| grouped train:',len(tr),'| grouped holdout:',len(te),'| classes:',y.nunique())
                for name, estimator in estimators.items():
                    estimator.fit(train_data.description.iloc[tr],y.iloc[tr])
                    pred=estimator.predict(train_data.description.iloc[te])
                    print(name,'accuracy:',round(accuracy_score(y.iloc[te],pred),4))
                    print(classification_report(y.iloc[te],pred,zero_division=0))
                    labels=sorted(y.unique())
                    display(pd.DataFrame(confusion_matrix(y.iloc[te],pred,labels=labels),index=labels,columns=labels))
                final_model=clone(estimators['MultinomialNB'])
                final_model.fit(train_data.description,y)
                trained_models[target]=final_model
                joblib.dump(final_model,OUTPUT/f'{target}_model.joblib')
                print('Saved artifact:',f'notebooks/output/{target}_model.joblib')
            if trained_models:
                predictions=df[['supermarket','item_name']].copy()
                for target,model in trained_models.items():
                    predictions[target+'_prediction']=model.predict(df.item_name.fillna('').astype(str))
                    print('Retail listing predicted distribution:',target)
                    display(predictions.groupby(['supermarket',target+'_prediction']).size().unstack(fill_value=0))
                predictions.to_csv(OUTPUT/'retailer_category_predictions.csv',index=False)
                print('Saved artifact: notebooks/output/retailer_category_predictions.csv')
                category_labels_path=ROOT/'backend/data/labels/category_sample.csv'
                labels_df=pd.read_csv(category_labels_path) if category_labels_path.exists() else pd.DataFrame()
                reviewed=labels_df[labels_df.label.fillna('').astype(str).str.strip().ne('')] if not labels_df.empty else labels_df
                if reviewed.empty:
                    print('labels not reviewed yet: edit backend/data/labels/category_sample.csv')
                else:
                    pred_map=dict(zip(df.id if 'id' in df else [x.id for x in listings],predictions.food_group_prediction))
                    y_true=reviewed.set_index('id').label.astype(str)
                    y_pred=pd.Series(pred_map).reindex(y_true.index)
                    valid=y_pred.notna()
                    if valid.any():
                        print('Reviewed retailer labels:',int(valid.sum()),'| domain shift: APHRC till-style wording vs retailer names.')
                        print(classification_report(y_true[valid],y_pred[valid],zero_division=0))
        if not trained_models:
            print('No APHRC model artifacts produced.')
    """, 6),
    markdown("""### 4b. Same-product matching

Blocking requires cross-store records with shared name tokens. Similarity averages TF-IDF cosine and token-set Dice overlap. A deterministic synthetic set is built from noisy copies of real listing descriptions and distinct real products; it is explicitly synthetic and does not estimate real-world matching performance. Human-label threshold and holdout metrics are computed only from the human `label` column, never `suggested_label`.
""", 7),
    code("""
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        from difflib import SequenceMatcher

        def normalize_sizes(value):
            return re.sub(r'(\\d)\\s+(kg|g|ml|l)\\b',r'\\1\\2',str(value).casefold())
        def token_set_ratio(a,b):
            A=set(re.findall(r'[a-z0-9]+',normalize_sizes(a))); B=set(re.findall(r'[a-z0-9]+',normalize_sizes(b)))
            return 2*len(A&B)/max(1,len(A)+len(B))
        def pair_score(a,b):
            matrix=TfidfVectorizer(ngram_range=(1,2)).fit_transform([normalize_sizes(a),normalize_sizes(b)])
            cosine=float(cosine_similarity(matrix[0],matrix[1])[0,0])
            return .5*cosine + .5*token_set_ratio(a,b)
        pair_df=pd.read_csv(ROOT/'backend/data/labels/match_pairs.csv')
        listing_by_id={x.id:x for x in listings}
        synthetic=[]
        def noisy_name(name,kind):
            if kind==0: return re.sub(r'(\\d)(ml|l|g|kg)\\b',r'\\1 \\2',name.lower())
            if kind==1: return ' '.join(reversed(name.split()))
            if kind==2: return re.sub(r'[^A-Za-z0-9 ]','',name)
            if len(name)>5: return name[:2]+name[3:]
            return name+' item'
        for i,item in enumerate(listings[:100]):
            synthetic.append((item.item_name,noisy_name(item.item_name,i%4),1))
        negatives=[]
        for _,row in pair_df.iterrows():
            a,b=listing_by_id.get(row.id_a),listing_by_id.get(row.id_b)
            if a and b and a.item_name.casefold()!=b.item_name.casefold():
                negatives.append((a.item_name,b.item_name,0))
        synthetic.extend(negatives[:len(synthetic)])
        sy=np.asarray([r[2] for r in synthetic])
        ss=np.asarray([pair_score(r[0],r[1]) for r in synthetic])
        indexes=np.arange(len(sy))
        tr,te=train_test_split(indexes,test_size=.3,random_state=42,stratify=sy)
        candidate_thresholds=np.linspace(0,1,101)
        synthetic_threshold=max(candidate_thresholds,key=lambda t:f1_score(sy[tr],ss[tr]>=t,zero_division=0))
        synthetic_pred=ss[te]>=synthetic_threshold
        print('SYNTHETIC only | train rows:',len(tr),'| test rows:',len(te),'| test positives:',int(sy[te].sum()))
        print('Synthetic threshold:',round(float(synthetic_threshold),3),'| precision/recall/F1:',
              precision_recall_fscore_support(sy[te],synthetic_pred,average='binary',zero_division=0)[:3])
        print('Synthetic confusion matrix [0,1]:\\n',confusion_matrix(sy[te],synthetic_pred,labels=[0,1]))
        human=pair_df[pair_df.label.fillna('').astype(str).str.strip().ne('')].copy()
        human_threshold=None
        if human.empty or human.label.astype(str).nunique()<2:
            print('labels not reviewed yet: edit backend/data/labels/match_pairs.csv')
            print('No real-pair matching metrics: human labels are not available in both classes.')
        else:
            hy=human.label.astype(int).to_numpy()
            hs=np.asarray([pair_score(a,b) for a,b in zip(human.name_a,human.name_b)])
            htr,hte=train_test_split(np.arange(len(hy)),test_size=.3,random_state=42,stratify=hy)
            human_threshold=max(candidate_thresholds,key=lambda t:f1_score(hy[htr],hs[htr]>=t,zero_division=0))
            hp=hs[hte]>=human_threshold
            print('HUMAN reviewed pairs:',len(human),'| holdout rows:',len(hte),'| holdout positives:',int(hy[hte].sum()))
            print('Human threshold:',round(float(human_threshold),3),'| precision/recall/F1:',
                  precision_recall_fscore_support(hy[hte],hp,average='binary',zero_division=0)[:3])
            print('Human confusion matrix [0,1]:\\n',confusion_matrix(hy[hte],hp,labels=[0,1]))
        threshold_artifact={'threshold':float(human_threshold if human_threshold is not None else synthetic_threshold),
                            'source':'human_review' if human_threshold is not None else 'synthetic',
                            'synthetic_threshold':float(synthetic_threshold),
                            'synthetic_test_rows':int(len(te)),
                            'human_reviewed_rows':int(len(human))}
        (OUTPUT/'match_threshold.json').write_text(json.dumps(threshold_artifact,indent=2),encoding='utf-8')
        print('Saved artifact: notebooks/output/match_threshold.json')
    """, 8),
    markdown("""## 5. Evaluation

APHRC holdout results describe catalogue language only. Retailer predictions have domain shift from APHRC till-style names to retailer descriptions. Synthetic matching metrics are a software check on controlled noisy copies, not a real-pair benchmark. Human label metrics remain pending review; suggestion columns are not labels.

## 6. Deployment

The API surfaces the dated snapshot and its caveats. Any operational use requires permission to use the data, repeated coverage, human-reviewed labels, validation against retailer checkout and stock information, privacy review, and drift monitoring. Saved files are local analysis artifacts under the Git-ignored `notebooks/output/` directory; this notebook does not claim a deployed model.
""", 9),
]

notebook = {
    "cells": cells,
    "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
    "nbformat": 4,
    "nbformat_minor": 5,
}
root = Path(__file__).resolve().parents[2]
destination = root / "notebooks/supermarket_listings_crisp_dm.ipynb"
destination.parent.mkdir(parents=True, exist_ok=True)
destination.write_text(json.dumps(notebook, indent=1), encoding="utf-8")
print("notebooks/supermarket_listings_crisp_dm.ipynb")
