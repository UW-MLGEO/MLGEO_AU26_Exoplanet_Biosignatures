# AGENTS.md

## Project
Finding Earth-like Chemistry in Exoplanets

We aim to identify molecular absorption features
in exoplanet atmospheric spectra using ML.

## Data
- Source: NASA Exoplanet Archive
- Data type: Atmospheric spectroscopy
- Inputs: Wavelength, flux or transit depth,
  and measurement uncertainties
- Preserve original data and physical units.
- Document preprocessing steps.
- Do not assume missing values are zero.

## Environment
Use Pixi for dependency management.

Install dependencies:
    pixi install

Run smoke test:
    pixi run smoke-test

## Machine Learning
- Baseline: Random Forest
- Proposed model: 1D CNN
- Focus on relevant molecular absorption bands.
- Avoid data leakage between training and test sets.
- Report metrics on independent test data.

## Reproducibility
- Use fixed random seeds where applicable.
- Keep raw data separate from processed data.
- Document all data transformations.
- Do not commit large datasets.