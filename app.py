"""
Claussifier API Server

FastAPI backend for legal clause risk classification.
Provides REST API endpoints for the trained BERT model.

Usage:
    python app.py

Then visit: http://localhost:8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
from pathlib import Path

# Import our modules
from src.inference.classifier import RiskClassifier
from src.inference.risk_explainer import RiskExplainer

# Initialize FastAPI app
app = FastAPI(
    title="Claussifier API",
    description="Legal Clause Risk Assessment API using BERT",
    version="1.0.0"
)

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
classifier = None
risk_explainer = None
current_model_name = "legalbert_with_augmentation_final_model"  # Default model (augmented with negation examples)

# Request/Response models
class ClassifyRequest(BaseModel):
    clause: str = Field(..., description="Legal clause text to classify", min_length=10)
    return_all_scores: bool = Field(False, description="Return scores for all categories")

class BatchClassifyRequest(BaseModel):
    clauses: List[str] = Field(..., description="List of clauses to classify")
    return_all_scores: bool = Field(False, description="Return scores for all categories")

class RiskInfo(BaseModel):
    risk_type: str
    confidence: float
    threshold: float

class ClassifyResponse(BaseModel):
    status: str = "success"
    data: dict

# Startup event - load model
@app.on_event("startup")
async def load_model(model_name: str = None):
    """Load the trained model on server startup or when switching models."""
    global classifier, current_model_name
    
    # Use provided model_name or current default
    if model_name:
        current_model_name = model_name
    
    # Path to model (adjust if needed)
    model_dir = Path(f"src/models/{current_model_name}")
    
    if not model_dir.exists():
        print("⚠ Model directory not found!")
        print(f"Expected location: {model_dir.absolute()}")
        print("\nPlease download the model from Google Drive:")
        print(f"  /MyDrive/Claussifier/models/{current_model_name}/")
        print(f"\nAnd place it in: src/models/{current_model_name}/")

        return
    
    try:
        classifier = RiskClassifier(model_dir=str(model_dir))
        print(f"✓ Model loaded successfully: {current_model_name}")
    except Exception as e:
        print(f"✗ Failed to load model: {e}")
    
    # Initialize risk explainer
    global risk_explainer
    risk_explainer = RiskExplainer()
    print("✓ Risk Explainer initialized")

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """API documentation page."""
    return """
    <html>
        <head>
            <title>Claussifier API</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }
                .container {
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                }
                h1 { margin-top: 0; font-size: 2.5em; }
                code {
                    background: rgba(0, 0, 0, 0.3);
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                }
                .endpoint {
                    background: rgba(255, 255, 255, 0.1);
                    padding: 15px;
                    margin: 10px 0;
                    border-radius: 10px;
                    border-left: 4px solid #4ade80;
                }
                a { color: #4ade80; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🔍 Claussifier API</h1>
                <p>Legal Clause Risk Assessment using BERT</p>
                
                <h2>📍 Endpoints</h2>
                
                <div class="endpoint">
                    <strong>POST /classify</strong><br>
                    Classify a single legal clause<br>
                    <code>{"clause": "Your clause text"}</code>
                </div>
                
                <div class="endpoint">
                    <strong>POST /classify-batch</strong><br>
                    Classify multiple clauses<br>
                    <code>{"clauses": ["Clause 1", "Clause 2"]}</code>
                </div>
                
                <div class="endpoint">
                    <strong>GET /model-info</strong><br>
                    Get model metadata and configuration
                </div>
                
                <div class="endpoint">
                    <strong>GET /health</strong><br>
                    Check API health status
                </div>
                
                <h2>📚 Documentation</h2>
                <p>
                    Interactive API docs: <a href="/docs">/docs</a><br>
                    Alternative docs: <a href="/redoc">/redoc</a>
                </p>
                
                <h2>🎨 Frontend</h2>
                <p>
                    Open <code>frontend/index.html</code> in your browser to use the web interface.
                </p>
            </div>
        </body>
    </html>
    """

# Health check
@app.get("/health")
async def health_check():
    """Check if API and model are ready."""
    return {
        "status": "healthy" if classifier is not None else "model_not_loaded",
        "model_loaded": classifier is not None
    }

# Model info
@app.get("/model-info")
async def get_model_info():
    """Get information about the loaded model."""
    if classifier is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    model_dir = Path(f"src/models/{current_model_name}")
    
    # Determine model display name based on current model
    if current_model_name == "legalbert_with_augmentation_final_model":
        default_name = "Legal-BERT + Negation Augmentation"
        default_type = "nlpaueb/legal-bert-base-uncased (augmented)"
    elif current_model_name == "legalbert_final_model":
        default_name = "Legal-BERT Risk Detector"
        default_type = "nlpaueb/legal-bert-base-uncased"
    else:
        default_name = "BERT-base Risk Detector"
        default_type = "bert-base-uncased"
    
    # Default values
    model_info = {
        "model_name": default_name,
        "model_type": default_type,
        "f1_score": 0.0,
        "precision": 0.0,
        "recall": 0.0
    }
    
    # Try to load from config.json if it exists
    config_path = model_dir / "config.json"
    if config_path.exists():
        try:
            import json
            with open(config_path, 'r') as f:
                config = json.load(f)
                
            # Extract metrics from config (convert decimals to percentages)
            if 'test_macro_f1' in config:
                model_info['f1_score'] = round(config['test_macro_f1'] * 100, 1)
            if 'test_macro_precision' in config:
                model_info['precision'] = round(config['test_macro_precision'] * 100, 1)
            if 'test_macro_recall' in config:
                model_info['recall'] = round(config['test_macro_recall'] * 100, 1)
            if 'model_name' in config:
                model_info['model_type'] = config['model_name']
        except Exception as e:
            print(f"Could not load config: {e}")
    
    # If precision/recall not in config, try to load from training report
    if model_info['precision'] == 0.0 or model_info['recall'] == 0.0:
        # Determine results directory based on model
        if current_model_name == "legalbert_with_augmentation_final_model":
            report_path = Path("src/results/legalbert_with_augmented_data/legalbert_training_report.txt")
        elif current_model_name == "legalbert_final_model":
            report_path = Path("src/results/legalbert/legalbert_training_report.txt")
        else:
            report_path = Path("src/results/bert/stage1_training_report.txt")
        
        if report_path.exists():
            try:
                with open(report_path, 'r') as f:
                    content = f.read()
                    
                # Parse macro precision and recall from report
                import re
                precision_match = re.search(r'Macro Metrics:.*?Precision:\s+([\d.]+)', content, re.DOTALL)
                recall_match = re.search(r'Macro Metrics:.*?Recall:\s+([\d.]+)', content, re.DOTALL)
                
                if precision_match:
                    model_info['precision'] = round(float(precision_match.group(1)) * 100, 1)
                if recall_match:
                    model_info['recall'] = round(float(recall_match.group(1)) * 100, 1)
            except Exception as e:
                print(f"Could not load training report: {e}")
    
    return {
        "status": "success",
        "data": model_info,
        "current_model": current_model_name
    }

# Switch model endpoint
@app.post("/switch-model")
async def switch_model(request: dict):
    """Switch to a different model."""
    global classifier, current_model_name
    
    model_name = request.get("model_name")
    if not model_name:
        raise HTTPException(status_code=400, detail="model_name is required")
    
    # Validate model name
    valid_models = ["bert_final_model", "legalbert_final_model", "legalbert_with_augmentation_final_model"]
    if model_name not in valid_models:
        raise HTTPException(status_code=400, detail=f"Invalid model. Choose from: {valid_models}")
    
    # Check if model exists
    model_dir = Path(f"src/models/{model_name}")
    if not model_dir.exists():
        raise HTTPException(status_code=404, detail=f"Model directory not found: {model_dir}")
    
    try:
        # Load new model
        current_model_name = model_name
        classifier = RiskClassifier(model_dir=str(model_dir))
        print(f"✓ Switched to model: {current_model_name}")
        
        return {
            "status": "success",
            "message": f"Successfully switched to {model_name}",
            "current_model": current_model_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

# Single clause classification
@app.post("/classify", response_model=ClassifyResponse)
async def classify_clause(request: ClassifyRequest):
    """
    Classify a single legal clause for risk assessment.
    
    Returns risk predictions with confidence scores and attention-based explanations.
    """
    if classifier is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Use classify_with_attention to get both classification and XAI data
        result = classifier.classify_with_attention(
            clause=request.clause,
            return_all_scores=request.return_all_scores
        )
        
        # Add risk explanations
        if result['is_risky'] and risk_explainer:
            for risk in result['risks_detected']:
                try:
                    explanation = risk_explainer.explain_risk(
                        clause=request.clause,
                        risk_type=risk['risk_type'],
                        confidence=risk['confidence'],
                        top_words=result['attention_explanation']['top_words']
                    )
                    risk['explanation'] = explanation
                except Exception as e:
                    print(f"Explanation generation failed for '{risk['risk_type']}': {e}")
                    # Continue without explanation
        
        return ClassifyResponse(
            status="success",
            data=result
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Classification failed: {str(e)}")

# Batch classification
@app.post("/classify-batch", response_model=ClassifyResponse)
async def classify_batch(request: BatchClassifyRequest):
    """
    Classify multiple legal clauses in batch.
    
    More efficient than calling /classify multiple times.
    """
    if classifier is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(request.clauses) == 0:
        raise HTTPException(status_code=400, detail="No clauses provided")
    
    if len(request.clauses) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 clauses per batch")
    
    try:
        results = classifier.classify_batch(
            clauses=request.clauses,
            return_all_scores=request.return_all_scores
        )
        
        return ClassifyResponse(
            status="success",
            data={
                "total_clauses": len(results),
                "risky_clauses": sum(1 for r in results if r['is_risky']),
                "safe_clauses": sum(1 for r in results if not r['is_risky']),
                "results": results
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch classification failed: {str(e)}")


# Batch classification with attention (XAI)
@app.post("/classify-batch-with-attention", response_model=ClassifyResponse)
async def classify_batch_with_attention(request: BatchClassifyRequest):
    """
    Classify multiple legal clauses with attention-based explanations (XAI).
    
    Returns classification results plus attention weights showing which
    words/phrases influenced the model's predictions.
    """
    if classifier is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if len(request.clauses) == 0:
        raise HTTPException(status_code=400, detail="No clauses provided")
    
    if len(request.clauses) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 clauses per batch")
    
    try:
        results = []
        
        # Process each clause with attention
        for clause in request.clauses:
            result = classifier.classify_with_attention(
                clause=clause,
                return_all_scores=request.return_all_scores
            )
            
            # Add risk explanations
            if result['is_risky'] and risk_explainer:
                for risk in result['risks_detected']:
                    try:
                        explanation = risk_explainer.explain_risk(
                            clause=clause,
                            risk_type=risk['risk_type'],
                            confidence=risk['confidence'],
                            top_words=result['attention_explanation']['top_words']
                        )
                        risk['explanation'] = explanation
                    except Exception as e:
                        print(f"Explanation generation failed for '{risk['risk_type']}': {e}")
                        # Continue without explanation
            
            results.append(result)
        
        return ClassifyResponse(
            status="success",
            data={
                "total_clauses": len(results),
                "risky_clauses": sum(1 for r in results if r['is_risky']),
                "safe_clauses": sum(1 for r in results if not r['is_risky']),
                "results": results
            }
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch classification with attention failed: {str(e)}")



# Run server
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*80)
    print("🚀 Starting Claussifier API Server")
    print("="*80)
    print("\nServer will be available at:")
    print("  • API: http://localhost:8000")
    print("  • Docs: http://localhost:8000/docs")
    print("  • Frontend: Open frontend/index.html in your browser")
    print("\n" + "="*80 + "\n")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
