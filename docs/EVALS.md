# Evaluation Methodology

## What gets evaluated

| Component | Metric | Method |
|---|---|---|
| Theme clustering | Assignment accuracy | Synthetic data has known planted themes (6 in the sample set) — measure % of records whose cluster matches their planted theme |
| Theme labels | Human preference | Blind A/B: keyword labels vs. LLM labels, judged on 30 clusters |
| Sentiment | Correlation with rating | Spearman correlation between lexicon score and user rating on records that have both |
| Brief | Citation integrity | Automated: every quoted string in the brief must be a substring of the record with the cited ID (zero tolerance) |
| Brief | Usefulness rubric | 1–5 on: prioritization correctness, evidence quality, actionability (LLM-as-judge with published rubric, spot-checked by hand) |

## Why synthetic data with planted themes

The sample generator plants 6 known themes with controlled sentiment/urgency profiles plus 40 noise records. Because ground truth is known, clustering quality is measurable without human labeling — the same trick applies when swapping embedding backends (TF-IDF vs. MiniLM) to quantify the upgrade.

## Baseline results

Populate this table by running the pipeline on `data/sample_feedback.csv`:

| Backend | Theme recovery | Noise handling | Notes |
|---|---|---|---|
| TF-IDF + SVD | _run and record_ | _run and record_ | zero-dependency default |
| MiniLM | _run and record_ | _run and record_ | optional upgrade |

## Known limitations

- Lexicon sentiment misses sarcasm and negation ("not great") — model swap planned, interface already stable
- LLM-as-judge rubric scores drift across model versions; pin the judge model and version the rubric
- Synthetic data is cleaner than production feedback; treat accuracy numbers as upper bounds
