import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

wavelengths = np.linspace(1, 5, 100)
flux = 1.0 - 0.1 * np.exp(-((wavelengths - 3.0) / 0.2) ** 2)

assert len(wavelengths) == len(flux)
assert np.all(np.isfinite(flux))

X = pd.DataFrame({"wavelength": wavelengths, "flux": flux})
y = (X["flux"] < 0.95).astype(int)

model = RandomForestClassifier(n_estimators=10, random_state=42)
model.fit(X, y)

assert len(model.predict(X)) == 100

print("Smoke test passed!")