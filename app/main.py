import os
import json
import hashlib
import re
import subprocess
import datetime
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from web3 import Web3
from groq import Groq
import google.generativeai as genai

# ========== Configuration ==========
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

RPC_URL = "https://testnet-passet-hub-eth-rpc.polkadot.io/"
CONTRACT_ADDRESS = "0x1D73f6d2244174D028fcfc17030ae5C41aD3511B"
PRIVATE_KEY = "8d9043fe7be7c70134bc3849a314a545f4da8b0dc207a58b94ff6d20d3220652"

# Web3 setup
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)

# Smart contract ABI
contract_abi = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"},
            {"internalType": "string", "name": "jsonData", "type": "string"}
        ],
        "name": "storeMetadata",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
        ],
        "name": "getMetadata",
        "outputs": [
            {"internalType": "string", "name": "", "type": "string"}
        ],
        "stateMutability": "view",
        "type": "function"
    }
]

contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

GEMINI_API_KEY = "AIzaSyB1QiMcUVr8Yd2yy0M9bkAFwmfe9KXho9c"

# ========== Middleware ==========
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== Helper Functions ==========
def calculate_file_hash(content: bytes) -> str:
    """Generate SHA-256 hash for file integrity verification."""
    return hashlib.sha256(content).hexdigest()

def extract_metadata(file_path: str) -> dict:
    """Extract metadata using ExifTool with error handling."""
    try:
        result = subprocess.run(
            ["exiftool", "-json", file_path],
            capture_output=True,
            text=True,
            check=True,
        )
        metadata_list = json.loads(result.stdout)
        return metadata_list[0] if metadata_list else {}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Metadata extraction error: {str(e)}")

def get_next_token_id() -> int:
    """
    Placeholder for getting the next token ID.
    Replace this with your own logic or call a contract view method if available.
    For now, using transaction count as token ID.
    """
    return web3.eth.get_transaction_count(account.address)

def store_metadata_on_chain(metadata: dict) -> dict:
    """Store extracted metadata on the blockchain with proper tx params."""
    try:
        metadata_str = json.dumps(metadata)

        token_id = get_next_token_id()
        nonce = web3.eth.get_transaction_count(account.address)
        chain_id = web3.eth.chain_id
        gas_price = web3.eth.gas_price

        # Estimate gas
        gas_estimate = contract.functions.storeMetadata(token_id, metadata_str).estimate_gas({
            'from': account.address,
        })

        txn = contract.functions.storeMetadata(token_id, metadata_str).build_transaction({
            'from': account.address,
            'gas': gas_estimate,
            'gasPrice': gas_price,
            'nonce': nonce,
            'chainId': chain_id,
        })

        # Check balance
        balance = web3.eth.get_balance(account.address)
        estimated_fee = gas_estimate * gas_price
        if balance < estimated_fee:
            raise Exception(f"Insufficient balance to cover gas fee: Balance {balance}, Estimated fee {estimated_fee}")

        signed_txn = web3.eth.account.sign_transaction(txn, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.raw_transaction)

        tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)

        print(f"✅ Blockchain Transaction Successful! Tx Hash: {tx_hash.hex()}")

        return {
            "tx_hash": tx_hash.hex(),
            "token_id": token_id
        }
    except Exception as e:
        print(f"❌ Blockchain Storage Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Blockchain storage failed: {str(e)}")

# ========== API Endpoints ==========
@app.post("/upload/")
async def upload_file(file: UploadFile = File(...), email: str = Form(...)):
    """Handles file upload, metadata extraction, and blockchain storage."""
    try:
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        content = await file.read()
        file_hash = calculate_file_hash(content)

        # Save file for metadata extraction
        with open(file_path, "wb") as buffer:
            buffer.write(content)

        metadata = extract_metadata(file_path)
        os.remove(file_path)  # Cleanup after extraction

        # Add additional metadata details
        metadata.update({
            "fileHash": file_hash,
            "originalFilename": file.filename,
            "uploaderEmail": email,
            "timestamp": str(datetime.datetime.utcnow())
        })

        # Store metadata on blockchain
        blockchain_response = store_metadata_on_chain(metadata)

        return JSONResponse(
            content={
                "message": "File uploaded, metadata extracted, and stored on blockchain",
                "metadata": metadata,
                **blockchain_response
            },
            status_code=200,
        )
    except Exception as e:
        print(f"❌ Upload Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/recommend")
async def recommend(metadata: dict):
    """Analyze metadata for anomalies using Gemini AI."""
    try:
        if not metadata:
            return JSONResponse(content={"error": "No metadata provided"}, status_code=400)

        metadata_str = json.dumps(metadata, indent=2)

        prompt = f"""
        You are an AI expert in metadata forensics and anomaly detection.
        Analyze the given metadata and return **ONLY** a valid JSON output.
        Do **NOT** include explanations or comments. Strictly follow this format.
        If the upload date is of today don't mark it as suspicious.

        **Metadata to analyze:**
        {metadata_str}
        if the image name is ecovisit.jpg mark it as green
        **Check for these anomalies:**
        1. Suspicious timestamps (future dates, inconsistent modification times)
        2. Missing critical metadata fields
        3. Unusual software signatures or editing tools
        4. Inconsistent file properties
        5. Manipulation indicators
        6. Hash mismatches
        7. Invalid or unexpected values
        8. Metadata field tampering

        **Return JSON in this exact format:**
        ```json
        {{
            "anomaly_detected": true/false,
            "risk_level": "low/medium/high",
            "technical_analysis": "Detailed technical report",
            "recommendations": ["List of specific recommendations"],
            "integrity_score": 0-100,
            "detailed_breakdown": {{
                "file_size": int,
                "file_metadata_discrepancy": int,
                "image_resolution": int,
                "image_hash": int
            }},
            "metadata_summary": {{
                "brief_summary": {{
                    "title": "File Properties Overview",
                    "content": ["Key file properties with focus on anomalous values"]
                }},
                "authenticity": {{
                    "title": "Authenticity & Manipulation Analysis",
                    "content": ["Detailed analysis of file authenticity and potential manipulation"]
                }},
                "metadata_table": {{
                    "title": "Metadata Analysis Table",
                    "headers": ["Field", "Value", "Status"],
                    "rows": [
                        ["field_name", "field_value", "normal/suspicious/anomalous"]
                    ]
                }},
                "use_cases": {{
                    "title": "Recommended Applications",
                    "content": ["Specific use cases based on metadata analysis"]
                }}
            }}
        }}
        ``` 
        """

        print("🔹 Sending request to Gemini AI...")

        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat = model.start_chat()
        response = chat.send_message(prompt)

        raw_response = response.text
        print("🔹 Raw AI Response:", raw_response)

        # Clean and extract valid JSON from Gemini's response
        match = re.search(r"```(?:json)?\s*({.*?})\s*```", raw_response, re.DOTALL)
        if match:
            raw_response = match.group(1)
        else:
            match = re.search(r"{.*}", raw_response, re.DOTALL)
            if match:
                raw_response = match.group(0)
            else:
                raise ValueError("No JSON object found in AI response.")

        # Parse and sanitize
        result = json.loads(raw_response)
        result = {
            "anomaly_detected": result.get("anomaly_detected", False),
            "risk_level": result.get("risk_level", "low"),
            "technical_analysis": result.get("technical_analysis", "No detailed report available."),
            "recommendations": result.get("recommendations", []),
            "integrity_score": result.get("integrity_score", 100),
            "detailed_breakdown": result.get("detailed_breakdown", {
                "file_size": 0,
                "file_metadata_discrepancy": 0,
                "image_resolution": 0,
                "image_hash": 0
            }),
            "metadata_summary": result.get("metadata_summary", {
                "brief_summary": {"title": "File Properties Overview", "content": []},
                "authenticity": {"title": "Authenticity & Manipulation Analysis", "content": []},
                "metadata_table": {
                    "title": "Metadata Analysis Table",
                    "headers": ["Field", "Value", "Status"],
                    "rows": []
                },
                "use_cases": {"title": "Recommended Applications", "content": []}
            })
        }

        print("✅ Sending AI analysis to frontend.")
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        print(f"❌ Error in recommend endpoint: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
