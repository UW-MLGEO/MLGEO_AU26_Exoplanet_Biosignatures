
# Finding Earth-like Chemistry in Exoplanets

**Team:** Nathan Yandell, Liam Randell, Kaira Nair

## Scientific Question

Can we use a machine learning algorithm to quickly and accurately find biosignature absorption lines in noisy exoplanet spectra from the James Webb Space Telescope (JWST)?

Exoplanet atmospheric spectroscopy is an important part of the search for life outside our solar system. By identifying molecular absorption lines in telescope spectra, we can look for evidence of potentially Earth-like chemistry in exoplanet atmospheres.

## Data

We will use atmospheric spectroscopy data from the NASA Exoplanet Archive. The data comes from published, peer-reviewed studies and includes measurements of wavelength, flux or transit depth, and associated uncertainties.

Dataset: https://exoplanetarchive.ipac.caltech.edu/cgi-bin/atmospheres/nph-firefly?atmospheres

We plan to focus on specific wavelength ranges associated with molecules such as CO2, CH4, and SO2. Some spectra have noise or missing data, so preprocessing and normalization may be needed before training the model.

### Downloading the Data

1. Open the NASA Exoplanet Archive link above.
2. Select relevant atmospheric spectra, focusing initially on transmission spectroscopy.
3. Download the selected spectra using the archive's download options.
4. Save the downloaded files in `data/raw/`.

## Machine Learning Approach

We plan to use machine learning to identify absorption features associated with different molecules in exoplanet atmospheres.

Our proposed approach is a 1D Convolutional Neural Network (CNN), which can learn patterns across different wavelengths in the spectra. We may also use a simpler model, such as Random Forest, as a baseline for comparison.

We plan to focus on relevant absorption bands rather than the entire spectrum, which may reduce the need for gap-filling.

We will investigate using synthetic spectra with added noise for training and testing.

## Evaluation

We plan to evaluate how accurately the model identifies molecular absorption features in noisy spectra and how well it performs on data it has not seen before.

Possible evaluation metrics include precision, recall, and F1-score.

## Project Timeline

- **November 2:** Further literature review and making the dataset AI-ready.
- **November 9:** Choose ML methods and prepare test data.
- **November 16:** Train the ML model.
- **November 23:** Run the model on the processed data.
- **November 30:** Write the final report.
- **December 7:** Prepare and practice the final presentation.

## Reproducibility

This repository uses Pixi to manage the Python environment and dependencies.

To install the environment:

```bash
pixi install
```

To run the smoke test:

```bash
pixi run smoke-test
```

The smoke test checks that the Python environment and basic ML packages work correctly.

### Repository Files

- `pixi.toml` — Project environment and dependencies.
- `pixi.lock` — Locked dependency versions.
- `AGENTS.md` — Project instructions.
- `scripts/smoke_test.py` — Basic environment smoke test.

## Reflection

**1. What did we learn?**
Our spectra had very different numbers of data points and covered different wavelength ranges, which made it difficult to compare them directly. We also learned why it is important to split the data carefully. Since some planets had multiple spectra, we had to make sure the same planet did not appear in both the training and test sets.

**2. What did we learn from using AI or chatbots?**
We used AI to help write some of the Python code, understand the rubric, and figure out how to analyze the dataset. However, we also learned that AI suggestions do not always work perfectly with real data. For example, our initial PCA approach assumed that all spectra shared a common wavelength range, which turned out not to be true. We had to check the results and adjust our approach.

**3. What would we improve about this assignment?**
We think it would be helpful to have more examples of how to prepare datasets that are not already in a consistent format. Our spectra came from different instruments and had different wavelength ranges, so some parts of the assignment were harder to apply directly. An example using this kind of scientific data would make it easier to understand how to handle these differences.