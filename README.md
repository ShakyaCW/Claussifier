# 🔍 Claussifier

**AI-Powered Legal Clause Risk Assessment Tool**

Claussifier uses BERT-based machine learning to automatically detect unfair and risky clauses in Terms of Service agreements and legal documents. Built with state-of-the-art NLP and explainable AI, it helps users understand the legal risks they're agreeing to.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688)](https://fastapi.tiangolo.com/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0%2B-EE4C2C)](https://pytorch.org/)
[![Transformers](https://img.shields.io/badge/🤗%20Transformers-4.35%2B-yellow)](https://huggingface.co/transformers/)

---

## 🎯 Features

- **🤖 AI-Powered Detection**: Identifies 8 types of risky clauses using fine-tuned BERT models
- **📊 Confidence Scores**: Shows how confident the model is about each detected risk
- **💡 Explainable AI**: Highlights influential words that led to the classification
- **📝 Plain Language Explanations**: Translates legal jargon into user-friendly descriptions
- **🌐 Multiple Interfaces**: Web UI, REST API, and Chrome extension
- **⚡ Batch Processing**: Analyze entire documents efficiently
- **🔄 Model Switching**: Choose between BERT-base, Legal-BERT, or augmented models

---

## 🚨 Risk Categories Detected

| Risk Type | Description |
|-----------|-------------|
| **Limitation of liability** | Company shields itself from legal responsibility for harm or loss |
| **Unilateral termination** | Company can delete your account/data without warning |
| **Unilateral change** | Company can change terms without notifying you |
| **Content removal** | Company can delete your content at their discretion |
| **Contract by using** | Using the service = automatic agreement to all terms |
| **Choice of law** | Disputes governed by laws from a different jurisdiction |
| **Jurisdiction** | Lawsuits must be filed in a specific (often distant) location |
| **Arbitration** | Waiver of right to sue in court or join class-action lawsuits |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend Layer                          │
│  ┌──────────────────┐         ┌──────────────────┐          │
│  │   Web UI         │         │ Chrome Extension │          │
│  │  (HTML/CSS/JS)   │         │   (Manifest V3)  │          │
│  └────────┬─────────┘         └────────┬─────────┘          │
└───────────┼──────────────────────────┼────────────────────┘
            │                          │
            └──────────┬───────────────┘
                       │ HTTP/REST
            ┌──────────▼──────────┐
            │   FastAPI Server    │
            │      (app.py)       │
            └──────────┬──────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
│ RiskClassifier│ │Attention │ │    Risk     │
│               │ │Explainer │ │  Explainer  │
└───────┬───────┘ └──────────┘ └─────────────┘
        │
        │ Loads Models
        │
┌───────▼────────────────────────────────────┐
│  BERT Models (PyTorch + Transformers)      │
│  • bert-base-uncased                       │
│  • legal-bert-base-uncased                 │
│  • legal-bert + negation augmentation ⭐   │
└────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager
- (Optional) CUDA-capable GPU for training

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/Claussifier.git
   cd Claussifier
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Download trained models**
   
   Download the pre-trained models from Google Drive and place them in `src/models/`:
   ```
   src/models/
   ├── bert_final_model/
   ├── legalbert_final_model/
   └── legalbert_with_augmentation_final_model/  ⭐ (recommended)
   ```

### Running the Application

#### 1. Start the API Server

```bash
python app.py
```

The server will start at:
- **API**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

#### 2. Use the Web Interface

Open `frontend/index.html` in your browser, or run:

```bash
python serve_frontend.py
```

Then visit http://localhost:8080

#### 3. Install Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (top right)
3. Click **Load unpacked**
4. Select the `chrome-extension/` directory
5. The extension icon will appear in your toolbar

---

## 📖 Usage Examples

### Web UI

1. Open the web interface
2. Paste a legal clause or full Terms of Service
3. Click "Analyze Clause"
4. View detected risks with confidence scores and explanations
5. See highlighted words that influenced the decision

### REST API

**Classify a single clause:**

```bash
curl -X POST "http://localhost:8000/classify" \
  -H "Content-Type: application/json" \
  -d '{
    "clause": "The company may terminate your account at any time without notice.",
    "return_all_scores": false
  }'
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "is_risky": true,
    "risks_detected": [
      {
        "risk_type": "Unilateral termination",
        "confidence": 0.94,
        "threshold": 0.5,
        "explanation": "The company can permanently delete your account and all your data at any time, for any reason (or no reason at all), without warning. You have no recourse or appeal process."
      }
    ],
    "safe_categories": ["Limitation of liability", "Arbitration", ...],
    "attention_explanation": {
      "top_words": [
        {"word": "terminate", "importance": 0.87},
        {"word": "account", "importance": 0.65},
        {"word": "without", "importance": 0.58}
      ]
    }
  }
}
```

**Batch classification:**

```bash
curl -X POST "http://localhost:8000/classify-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "clauses": [
      "We may change these terms at any time.",
      "You agree to binding arbitration.",
      "This is a standard privacy clause."
    ]
  }'
```

### Python Client

```python
import requests

# Classify a clause
response = requests.post(
    "http://localhost:8000/classify",
    json={
        "clause": "We reserve the right to modify these terms without notice.",
        "return_all_scores": False
    }
)

result = response.json()
if result['data']['is_risky']:
    print("⚠️ Risky clause detected!")
    for risk in result['data']['risks_detected']:
        print(f"  • {risk['risk_type']}: {risk['confidence']:.0%} confidence")
        print(f"    {risk['explanation']}")
```

### Chrome Extension

1. Navigate to any website with Terms of Service
2. Click the Claussifier extension icon
3. The extension will analyze the page content
4. Risky clauses will be highlighted directly on the page
5. Click highlighted text to see detailed explanations

---

## 🧪 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/classify` | POST | Classify a single clause with XAI explanations |
| `/classify-batch` | POST | Classify multiple clauses (up to 100) |
| `/classify-batch-with-attention` | POST | Batch classification with attention weights |
| `/model-info` | GET | Get current model metadata and performance |
| `/switch-model` | POST | Switch between available models |
| `/health` | GET | Check API health status |
| `/docs` | GET | Interactive API documentation (Swagger UI) |
| `/redoc` | GET | Alternative API documentation (ReDoc) |

---

## 🎓 Training Your Own Models

The project includes Jupyter notebooks for the complete training pipeline:

### Training Pipeline

1. **Exploratory Data Analysis** (`notebooks/01_eda.ipynb`)
   - Load LexGLUE unfair_tos dataset
   - Analyze label distribution and class imbalance
   - Visualize clause lengths and co-occurrence patterns

2. **Stage 1: BERT-base Training** (`notebooks/02_01_stage1_training.ipynb`)
   - Train bert-base-uncased on legal clauses
   - Multi-label classification with class weighting

3. **Threshold Optimization** (`notebooks/02_02_threshold_optimization.ipynb`)
   - Optimize decision thresholds per risk category
   - Maximize F1 score for each class

4. **Legal-BERT Training** (`notebooks/03_legalbert_training.ipynb`)
   - Fine-tune legal-bert-base-uncased
   - Better performance on legal terminology

5. **Data Augmentation** (`notebooks/04_data_augmentation_negation.ipynb`)
   - Generate negation examples
   - Reduce false positives

6. **Final Model** (`notebooks/05_legalbert_with_augmented_data.ipynb`)
   - Train Legal-BERT with augmented data
   - Current model in production

### Running in Google Colab

All notebooks are designed to run in Google Colab with GPU acceleration:

1. Upload notebooks to Google Drive
2. Open with Google Colab
3. Enable GPU: Runtime → Change runtime type → GPU
4. Run cells sequentially
5. Models are saved to Google Drive

---

## 📊 Model Performance

| Model | F1 Score | Precision | Recall |
|-------|----------|-----------|--------|
| BERT-base (with optimized thresholds) | 76.2% | 72.0% | 83.5% |
| Legal-BERT | 78.6% | 73.2% | 86.3% |
| Legal-BERT + Augmentation | 70.5% | 60.4% | 86.3% |

*Macro-averaged metrics on test set*

---

## 🗂️ Project Structure

```
Claussifier/
├── app.py                    # FastAPI server (main entry point)
├── serve_frontend.py         # Simple HTTP server for frontend
├── requirements.txt          # Python dependencies
├── .env                      # Environment variables
│
├── src/
│   ├── inference/
│   │   ├── classifier.py            # RiskClassifier (main logic)
│   │   ├── attention_explainer.py   # XAI attention weights
│   │   └── risk_explainer.py        # Plain language explanations
│   ├── models/                      # Trained model files
│   ├── results/                     # Training reports
│   └── visualizations/              # EDA charts
│
├── frontend/
│   ├── index.html           # Web UI
│   ├── script.js            # Frontend logic
│   └── style.css            # Professional styling
│
├── chrome-extension/
│   ├── manifest.json        # Extension config
│   ├── popup.html           # Extension popup
│   ├── content.js           # Page interaction
│   └── background.js        # Service worker
│
└── notebooks/               # Training pipeline
    ├── 01_eda.ipynb
    ├── 02_01_stage1_training.ipynb
    ├── 02_02_threshold_optimization.ipynb
    ├── 03_legalbert_training.ipynb
    ├── 04_data_augmentation_negation.ipynb
    └── 05_legalbert_with_augmented_data.ipynb
```

---

## 🛠️ Tech Stack

- **Backend**: FastAPI, Uvicorn
- **ML Framework**: PyTorch, Transformers (Hugging Face)
- **Models**: BERT-base, Legal-BERT
- **Data**: LexGLUE unfair_tos dataset (5,532 clauses)
- **Frontend**: Vanilla HTML/CSS/JavaScript
- **Browser Extension**: Chrome Extension (Manifest V3)
- **Training**: Google Colab (GPU-accelerated)

---

## 🧪 Testing

Run the test suite:

```bash
# Test model loading
python test_model_loading.py

# Test model info endpoint
python test_model_info.py

# Test XAI explanations
python test_xai.py

# Test data augmentation
python test_negation_augmentation.py
```
