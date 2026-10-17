# 🚀 Junior Space

**Draw in the air. Solve with AI. Learn without limits.**

Junior Space is an AI-powered interactive workspace that lets you draw using hand gestures in front of your webcam and solve mathematical problems with Google's Gemini AI. No physical whiteboard, stylus, or touchscreen required — just your hand and a camera.

## ✨ Features

- ✍️ **Air Drawing** — Draw on a virtual canvas using your index finger.
- 🧠 **AI-Powered Math Solving** — Submit your handwritten equations and mathematical problems to Gemini AI.
- 🖐️ **Gesture-Based Controls** — Control the workspace naturally with hand gestures.
- ↩️ **Undo Strokes** — Remove your last stroke using a gesture.
- 🧹 **Gesture Reset** — Clear the canvas without clicking a button.
- ⏸️ **Pause Generation** — Resume drawing if you no longer want to wait for an AI response.
- 📷 **Camera Controls** — Turn the webcam on or off whenever needed.
- 💎 **Modern Interface** — A responsive, minimal interface with a glassmorphism-inspired design.
- 🔒 **Local Webcam Processing** — Hand tracking and drawing run locally; only submitted canvas content is sent to Gemini for AI processing.

## 🖐️ Gesture Controls

| Gesture | Action |
|---|---|
| ☝️ Index finger extended | Draw on the canvas |
| 🤟 Three fingers extended | Undo the last stroke |
| 👍 Thumb only extended | Clear the canvas |
| 🖐️ Open palm | Submit the drawing to Gemini AI |

**Tip:** Hold a gesture steadily for a short moment to trigger the corresponding action.

## 🛠️ Tech Stack

| Technology | Purpose |
|---|---|
| Python | Core application logic |
| Flask | Backend and HTTP endpoints |
| OpenCV | Webcam capture and image processing |
| MediaPipe Tasks | Real-time hand landmark detection |
| NumPy | Canvas and image operations |
| Google Gemini API | AI-powered problem solving |
| HTML, CSS & JavaScript | Frontend and interactive interface |
| MathJax | Mathematical expression rendering |

## 📁 Project Structure

```text
Junior-Space/
├── main.py
├── requirements.txt
├── .env                  # API key — never commit this file
├── models/
│   └── hand_landmarker.task
├── templates/
│   ├── index.html
│   └── ai_board.html
└── static/
    ├── css/
    │   └── index.css
    └── js/
        └── junior-space.js
```

## ⚙️ Getting Started

### Prerequisites

- Python installed on your system
- A webcam
- A Google Gemini API key
- The MediaPipe hand landmark model at `models/hand_landmarker.task`

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/Junior-Space.git
cd Junior-Space
```

Replace `YOUR_USERNAME` with your GitHub username.

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Replace the placeholder with your actual API key. **Never commit your `.env` file or expose your API key publicly.**

### 5. Run the Application

```bash
python main.py
```

Open the local URL shown in the terminal, usually:

```text
http://127.0.0.1:5000
```

Allow camera access if your browser requests permission.

## 🔄 How It Works

1. **Capture:** The webcam captures video frames.
2. **Track:** MediaPipe detects hand landmarks and identifies gestures.
3. **Draw:** Your index finger controls strokes on the virtual canvas.
4. **Submit:** An open-palm gesture submits the current drawing for analysis.
5. **Solve:** Gemini processes the submitted content and generates a response.
6. **Display:** The answer appears in the floating answer panel.

## 🔐 Privacy & Security

- Keep API keys in environment variables.
- Exclude `.env`, virtual environments, and Python cache files from Git.
- Hand tracking and canvas drawing are designed to run locally.
- The submitted drawing is sent to the configured Gemini API for processing.
- Camera access can be turned off from the interface.

Review the implementation and your API provider's policies before deploying publicly.

## 🗺️ Roadmap

- [ ] Improve gesture recognition accuracy.
- [ ] Support more mathematical symbols and complex equations.
- [ ] Improve AI reasoning and answer formatting.
- [ ] Add more interactive learning capabilities.
- [ ] Explore additional AI-powered workspace features.

## 🤝 Contributing

Contributions, ideas, bug reports, and feature suggestions are welcome.

1. Fork the repository.
2. Create a feature branch.
3. Commit your changes.
4. Open a pull request.

## 📄 License

No license has been specified yet. Add a `LICENSE` file when you decide how others may use, modify, and distribute this project.

---

**Built with curiosity, code, and AI.** 🚀