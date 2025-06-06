import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Set random seed for reproducibility
np.random.seed(42)

# Number of normal and anomalous records
num_normal = 950
num_anomalies = 50
total_records = num_normal + num_anomalies

# Function to generate random timestamps within a range
def random_timestamp(start_date, end_date):
    delta = end_date - start_date
    random_days = np.random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)

# Define normal metadata values
start_date = datetime(2023, 1, 1)
end_date = datetime(2025, 4, 21)
#end_date = datetime(2024, 1, 1)

normal_metadata = {
    "file_size_kb": np.random.normal(500, 100, num_normal),  # Normal file size
    "created_date": [random_timestamp(start_date, end_date) for _ in range(num_normal)],
    "modified_date": [random_timestamp(start_date, end_date) for _ in range(num_normal)],
    "accessed_date": [random_timestamp(start_date, end_date) for _ in range(num_normal)],
    "software_used": np.random.choice(["Adobe Photoshop", "MS Word", "GIMP", "VLC Media Player"], num_normal),
    "author": np.random.choice(["Alice", "Bob", "Charlie", "David"], num_normal),
    "resolution_dpi": np.random.normal(300, 50, num_normal),  # Normal DPI range
}

# Convert normal metadata dates to string format
for key in ["created_date", "modified_date", "accessed_date"]:
    normal_metadata[key] = [date.strftime("%Y-%m-%d %H:%M:%S") for date in normal_metadata[key]]

# Convert to DataFrame
df_normal = pd.DataFrame(normal_metadata)
df_normal["label"] = 0  # Normal instances labeled as 0

# Introduce anomalies
anomaly_metadata = {
    "file_size_kb": np.concatenate([
        np.random.normal(5000, 2000, num_anomalies // 2),  # Abnormally large
        np.random.normal(10, 5, num_anomalies // 2)  # Abnormally small
    ]),
    "created_date": ["2099-12-31 23:59:59"] * (num_anomalies // 2) + 
                    ["1990-01-01 00:00:00"] * (num_anomalies // 2),  # Impossible dates
    "modified_date": ["2100-01-01 00:00:00"] * (num_anomalies // 2) + 
                     ["1980-01-01 00:00:00"] * (num_anomalies // 2),
    "accessed_date": ["2101-01-01 12:34:56"] * (num_anomalies // 2) + 
                     ["1970-01-01 05:43:21"] * (num_anomalies // 2),
    "software_used": np.random.choice(["Unknown Malware", "Hacked Tool v1.0"], num_anomalies),
    "author": np.random.choice(["Unknown", "Hacker123", "Anonymous"], num_anomalies),
    "resolution_dpi": np.concatenate([
        np.random.normal(50, 10, num_anomalies // 2),  # Unusual DPI (too low)
        np.random.normal(2000, 500, num_anomalies // 2)  # Unusual DPI (too high)
    ]),
}

# Convert to DataFrame
df_anomalies = pd.DataFrame(anomaly_metadata)
df_anomalies["label"] = 1  # Anomalous instances labeled as 1

# Combine both datasets
df = pd.concat([df_normal, df_anomalies], ignore_index=True)

# Save to CSV
csv_filename = "synthetic_metadata.csv"
df.to_csv(csv_filename, index=False)

print(f"✅ Synthetic metadata dataset saved as '{csv_filename}'")
