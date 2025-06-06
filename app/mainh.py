from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import subprocess
import json
import joblib  # For loading Isolation Forest model
import numpy as np
import pandas as pd
from groq import Groq
from sklearn.ensemble import IsolationForest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load pre-trained Isolation Forest model
MODEL_PATH = "./isolation_forest_model.pkl"  
try:
    iso_forest = joblib.load(MODEL_PATH)
except Exception as e:
    raise RuntimeError(f"❌ Model loading failed: {str(e)}")

def extract_metadata(file_path: str):
    try:
        result = subprocess.run(
            ["exiftool", "-json", file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        metadata_list = json.loads(result.stdout)
        return metadata_list[0] if metadata_list else {}

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="ExifTool not found. Please install it.")
    except subprocess.CalledProcessError:
        raise HTTPException(status_code=500, detail="Error extracting metadata.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid metadata format.")

def preprocess_metadata(metadata: dict):
    """ Convert metadata into a numerical format for Isolation Forest. """
    try:
        df = pd.DataFrame([metadata])  # Convert dictionary to DataFrame
        
        # Select only numeric columns (filtering out non-numeric metadata)
        df_numeric = df.select_dtypes(include=[np.number])

        if df_numeric.empty:
            raise ValueError("No numeric metadata found for anomaly detection.")
        
        return df_numeric.values  # Convert to NumPy array for model prediction
    except Exception as e:
        print(f"❌ Metadata preprocessing failed: {str(e)}")
        return None

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), email: str = Form(...)):
    try:
        file_path = f"./uploads/{file.filename}"
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        metadata = extract_metadata(file_path)
        
        os.remove(file_path)

        return JSONResponse(
            content={"message": "File uploaded successfully", "metadata": metadata},
            status_code=200,
        )
    except Exception as e:
        print(f"❌ Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")

client = Groq(api_key="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")

@app.post("/recommend/")
async def recommend(metadata: dict):
    try:
        # Preprocess metadata
        processed_metadata = preprocess_metadata(metadata)
        if processed_metadata is None:
            return JSONResponse(
                content={"error": "Metadata preprocessing failed. Unable to analyze."},
                status_code=500,
            )

        # Perform anomaly detection using Isolation Forest
        anomaly_score = iso_forest.decision_function(processed_metadata)[0]
        anomaly_prediction = iso_forest.predict(processed_metadata)[0]  # -1 (anomaly), 1 (normal)
        anomaly_detected = True if anomaly_prediction == -1 else False

        metadata_str = json.dumps(metadata, indent=2)

        prompt = f"""
        You are an AI expert in file metadata forensics.
        - Analyze the metadata below for inconsistencies.
        - Isolation Forest anomaly detection result: {"Anomalous" if anomaly_detected else "Normal"}
        - If an anomaly is found, explain why.
        - Regardless of anomaly detection, always provide best-practice recommendations to enhance metadata security.

        Metadata:
        {metadata_str}

        Return the response in strict JSON format:
        {{
            "anomaly_detected": {anomaly_detected},
            "reason": "Explanation of anomaly (if any, else say 'No issues detected.')",
            "recommendations": ["List of recommendations if an anomaly is detected, else keep this empty."],
            "best_practices": ["List of best-practice security tips if no anomaly is found."]
        }}
        """
        
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="qwen-2.5-coder-32b",
            temperature=0.3,
            max_tokens=400,
        )

        result = json.loads(response.choices[0].message.content)

        # Ensure correct structure
        if "best_practices" not in result:
            result["best_practices"] = []
        if "recommendations" not in result:
            result["recommendations"] = []

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        print(f"❌ Recommendation error: {str(e)}")
        raise HTTPException(status_code=500, detail="Recommendation generation failed")
