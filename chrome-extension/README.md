# 🔍 Claussifier Chrome Extension

**Analyze Terms of Service in Real-Time While You Browse**

The Claussifier Chrome Extension automatically detects and highlights risky clauses in Terms of Service agreements directly on web pages. No copy-pasting required—just browse and get instant legal risk assessments.

---

## ✨ Features

- **🎯 Automatic Detection**: Identifies ToS pages and analyzes them automatically
- **🔴 Visual Highlighting**: Risky clauses highlighted in red/yellow directly on the page
- **📊 Risk Badge**: Extension icon shows overall risk level (High/Medium/Low)
- **💡 Instant Explanations**: Click any highlighted clause for detailed risk information
- **📈 Summary Dashboard**: View all detected risks in a clean popup interface
- **📄 Export Reports**: Download analysis results as JSON or text
- **⚡ Real-Time Analysis**: Powered by the Claussifier API running locally

---

## 🚀 Installation

### Prerequisites

1. **Start the Claussifier API server** (required for the extension to work):
   ```bash
   cd c:\Projects\Claussifier\Claussifier
   python app.py
   ```
   
   The API should be running at `http://localhost:8000`

2. **Google Chrome** browser (version 88 or higher)

### Install Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle switch in top-right corner)
3. Click **"Load unpacked"**
4. Navigate to and select the folder:
   ```
   c:\Projects\Claussifier\Claussifier\chrome-extension
   ```
5. The Claussifier extension should now appear in your extensions list
6. (Optional) Pin the extension to your toolbar for easy access

---

## 📖 How to Use

### Automatic Analysis

The extension automatically activates on pages containing Terms of Service:

1. **Navigate to any ToS page** (e.g., Twitter, Google, Facebook terms)
2. **Wait for analysis** (usually 2-5 seconds)
3. **View results**:
   - Extension badge shows risk level (🔴 High / 🟡 Medium / 🟢 Low)
   - Risky clauses are highlighted on the page
   - Click any highlighted text for detailed explanation

### Manual Analysis

For pages not automatically detected:

1. Click the **Claussifier extension icon** in your toolbar
2. Click **"Analyze This Page"** button
3. Wait for analysis to complete
4. View highlighted clauses and risk summary

### View Risk Summary

1. Click the **extension icon** to open the popup
2. See:
   - Overall risk level
   - Number of risky clauses detected
   - List of all detected risks with confidence scores
   - Quick explanations for each risk type

### Export Analysis

1. Open the extension popup
2. Click **"Export Report"** button
3. Choose format (JSON or Text)
4. Save the report to your computer

---

## 🧪 Test Sites

Try the extension on these popular Terms of Service pages:

| Website | URL | Expected Risks |
|---------|-----|----------------|
| **Twitter/X** | https://twitter.com/tos | High (multiple risks) |
| **Google** | https://policies.google.com/terms | Medium-High |
| **Facebook** | https://www.facebook.com/legal/terms | High |
| **Instagram** | https://help.instagram.com/581066165581870 | High |
| **Reddit** | https://www.redditinc.com/policies/user-agreement | Medium-High |
| **Discord** | https://discord.com/terms | Medium |
| **Spotify** | https://www.spotify.com/legal/end-user-agreement/ | Medium |
| **Netflix** | https://help.netflix.com/legal/termsofuse | Medium |

---

## 🎨 User Interface

### Extension Badge

The extension icon badge shows the overall risk level:

- **🔴 Red (High)**: 3+ risky clauses detected
- **🟡 Yellow (Medium)**: 1-2 risky clauses detected
- **🟢 Green (Low)**: No significant risks detected
- **⚪ Gray**: Page not analyzed or analysis failed

### Highlighted Clauses

Risky clauses are highlighted directly on the page:

- **Red background**: High-confidence risk detection (>70%)
- **Yellow background**: Medium-confidence risk (50-70%)
- **Hover effect**: Clause becomes more prominent on mouse hover
- **Click**: Opens detailed modal with risk explanation

### Popup Dashboard

Click the extension icon to see:

```
┌─────────────────────────────────────┐
│  🔍 Claussifier                     │
├─────────────────────────────────────┤
│  Risk Level: 🔴 HIGH                │
│  Risky Clauses: 5                   │
├─────────────────────────────────────┤
│  Detected Risks:                    │
│                                     │
│  ⚠️ Unilateral Termination          │
│     Confidence: 94%                 │
│     The company can delete your...  │
│                                     │
│  ⚠️ Arbitration                     │
│     Confidence: 87%                 │
│     You waive your right to sue...  │
│                                     │
│  [View All Risks]                   │
│  [Export Report]                    │
└─────────────────────────────────────┘
```

---

## 🏗️ Technical Architecture

### Extension Components

```
chrome-extension/
├── manifest.json          # Extension configuration (Manifest V3)
├── content.js            # Injected into web pages (clause detection)
├── background.js         # Service worker (badge management)
├── popup.html            # Extension popup UI
├── popup.js              # Popup logic and API communication
├── styles.css            # Extension styling
└── icons/                # Extension icons (16x16, 48x48, 128x128)
```

### How It Works

1. **Page Detection** (`content.js`):
   - Monitors page loads
   - Detects ToS pages by URL patterns and keywords
   - Extracts text content from the page

2. **API Communication** (`popup.js`):
   - Sends extracted text to Claussifier API
   - Receives risk classifications and explanations
   - Handles batch processing for long documents

3. **Visual Highlighting** (`content.js`):
   - Identifies risky text spans on the page
   - Applies CSS highlighting
   - Adds click handlers for detailed modals

4. **Badge Updates** (`background.js`):
   - Calculates overall risk level
   - Updates extension icon badge
   - Manages extension state

### API Integration

The extension communicates with the local Claussifier API:

```javascript
// Example API call from popup.js
fetch('http://localhost:8000/classify-batch', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    clauses: extractedClauses,
    return_all_scores: false
  })
})
```

---

## 🔧 Configuration

### Change API Endpoint

If your API runs on a different port, edit `popup.js`:

```javascript
// Line ~10
const API_BASE_URL = 'http://localhost:8000';  // Change this
```

### Customize Highlighting Colors

Edit `styles.css` to change highlight colors:

```css
.claussifier-risk-high {
  background-color: rgba(255, 0, 0, 0.3);  /* Red for high risk */
}

.claussifier-risk-medium {
  background-color: rgba(255, 165, 0, 0.3);  /* Orange for medium */
}
```

### Adjust Auto-Detection

Modify URL patterns in `content.js`:

```javascript
// Line ~15
const TOS_PATTERNS = [
  /terms/i,
  /tos/i,
  /service/i,
  /policy/i,
  /agreement/i,
  // Add your patterns here
];
```

---

## 🐛 Troubleshooting

### Extension Doesn't Activate

**Problem**: Extension badge stays gray on ToS pages

**Solutions**:
- Check if the page URL contains keywords like "terms", "tos", "policy"
- Manually click the extension icon and select "Analyze This Page"
- Refresh the page after loading the extension

### No Highlighting Appears

**Problem**: Analysis completes but no clauses are highlighted

**Solutions**:
1. Open browser console (F12) and check for errors
2. Verify the API is running: visit http://localhost:8000/health
3. Check CORS is enabled in `app.py`
4. Try refreshing the page

### API Connection Fails

**Problem**: "Failed to connect to API" error

**Solutions**:
1. Ensure `python app.py` is running in terminal
2. Check the API is accessible: http://localhost:8000
3. Verify firewall isn't blocking localhost connections
4. Check the API endpoint in `popup.js` matches your server

### Badge Doesn't Update

**Problem**: Badge shows wrong risk level or doesn't change

**Solutions**:
- Refresh the page
- Check background service worker console:
  - Go to `chrome://extensions/`
  - Click "service worker" under Claussifier
  - Look for errors in the console

### Extension Slows Down Browser

**Problem**: Page loads slowly with extension enabled

**Solutions**:
- Disable auto-analysis for large documents
- Use manual analysis mode instead
- Increase batch size in API calls (edit `popup.js`)

---

## 🔒 Privacy & Security

### Data Handling

- **No data collection**: The extension does NOT collect or store any personal data
- **Local processing**: All analysis happens on your computer via localhost API
- **No external servers**: Text is never sent to external servers
- **No tracking**: No analytics, cookies, or user tracking

### Permissions Explained

The extension requires these permissions:

| Permission | Purpose |
|------------|---------|
| `activeTab` | Access current tab content to extract ToS text |
| `scripting` | Inject content script for highlighting clauses |
| `storage` | Save user preferences (analysis settings) |
| `host_permissions` | Connect to localhost API (http://localhost:8000) |

### Security Best Practices

- ✅ Only analyzes text content (no form data or passwords)
- ✅ Uses Manifest V3 (latest security standards)
- ✅ No eval() or unsafe code execution
- ✅ Content Security Policy enforced
- ✅ Minimal permissions requested

---

## 🚧 Known Limitations

- **Requires local API**: Extension won't work without the API server running
- **English only**: Currently only supports English-language ToS
- **Text-based**: Cannot analyze ToS in images or PDFs embedded in pages
- **Page structure**: May miss clauses in dynamically loaded content
- **Performance**: Large documents (>10,000 words) may take 10-20 seconds

---

## 🔮 Roadmap

### Upcoming Features

- [ ] **Offline mode**: Bundled lightweight model for basic analysis
- [ ] **PDF support**: Analyze PDF ToS documents
- [ ] **Multi-language**: Support for Spanish, French, German
- [ ] **Comparison mode**: Compare ToS across different services
- [ ] **History tracking**: Track ToS changes over time
- [ ] **Browser notifications**: Alert when visiting high-risk sites
- [ ] **Firefox & Edge**: Support for other browsers

### Future Enhancements

- [ ] Cloud API option (for users without local setup)
- [ ] Custom risk thresholds
- [ ] Export to PDF with highlighted clauses
- [ ] Integration with legal databases
- [ ] Collaborative risk reporting

---

## 🛠️ Development

### Build from Source

```bash
# Clone repository
git clone https://github.com/yourusername/Claussifier.git
cd Claussifier/chrome-extension

# Make your changes to the extension files
# No build step required - it's vanilla JavaScript!

# Reload extension in Chrome
# Go to chrome://extensions/ and click the reload icon
```

### Testing

1. **Unit tests**: (Coming soon)
2. **Manual testing**: Use the test sites listed above
3. **Console logging**: Check browser console for debug info

### Contributing

Contributions welcome! Focus areas:

- Improve clause extraction algorithm
- Better handling of dynamic content
- UI/UX enhancements
- Performance optimizations
- Bug fixes

---

## 📄 License

This extension is part of the Claussifier project and is licensed under the MIT License.

---

## 🙏 Acknowledgments

- Built with Chrome Extension Manifest V3
- Powered by Claussifier API (FastAPI + BERT)
- Icons from [source] (if applicable)

---

## 📧 Support

**Issues?** Open an issue on GitHub or check the main project README.

**Questions?** See the [main Claussifier documentation](../README.md)

---

## ⚖️ Legal Disclaimer

**This extension is an educational tool and should not replace professional legal advice.** The risk assessments are based on machine learning models and may not be 100% accurate. Always consult with a qualified attorney for legal matters.

---

<div align="center">

**Browse smarter. Read safer. 🔍**

Part of the [Claussifier Project](../README.md)

</div>
