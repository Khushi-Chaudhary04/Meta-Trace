import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import IsolationForest
from sklearn.model_selection import train_test_split

DATASET_PATH = "metadata_dataset.csv"

df = pd.read_csv(DATASET_PATH)


df_numeric = df.select_dtypes(include=[np.number])

if df_numeric.empty:
    raise ValueError("No numeric metadata found for anomaly detection.")

X_train, X_test = train_test_split(df_numeric, test_size=0.2, random_state=42)

iso_forest = IsolationForest(
    n_estimators=100,  
    contamination=0.05,  
    random_state=42
)
iso_forest.fit(X_train)

MODEL_PATH = "isolation_forest_model.pkl"
joblib.dump(iso_forest, MODEL_PATH)
