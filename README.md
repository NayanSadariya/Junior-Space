# AI-Based Air Drawing & Learning System

An interactive, AI-powered web application that allows users to draw mathematical problems either virtually in the air using hand gestures via a webcam, or on a 2D digital canvas. The system captures the drawings, recognizes the handwriting, and provides detailed, step-by-step mathematical solutions using the advanced Google Gemini AI engine.

---

## 🚀 Key Features

### 1. 🖐️ Virtual Draw (Webcam Mode)
* **Real-time Gesture Tracking:** Uses OpenCV and MediaPipe Hand Landmarking to track hand movements.
* **On-screen UI Controls:** Select drawing colors (Blue, Green, Red, Yellow) or clear the canvas by hovering your index finger over visual buttons.
* **Smart Pen Mechanics:** Draw seamlessly by pointing your index finger. Pause drawing/raise the pen by bringing your thumb and index finger close together (pinching gesture).
* **AI Analysis:** Capture your air drawings and send them to Google Gemini for real-time mathematical analysis.

### 2. 🎨 AI Board (Digital Canvas Mode)
* **Interactive 2D Sketchpad:** Draw directly on the screen using a mouse, stylus, or trackpad on an HTML5 canvas.
* **Customization Tools:** Adjust brush sizes, select any color from a color picker, or use the eraser tool.
* **AI Problem Solver:** Write complex math equations or draw questions, then click **Solve Problem** to get step-by-step guidance.

### 3. 🧠 Gemini AI Integration
* Powered by the state-of-the-art `gemini-2.0-flash` model.
* High-accuracy OCR (Optical Character Recognition) for handwritten text/symbols.
* Step-by-step educational explanations tailored for easy learning.

---

## 📂 Project Structure

```text
├── Air-Canvas-with-ML/         # Legacy folder
└── air_drawing/
    ├── main.py                 # Flask server, OpenCV/MediaPipe pipeline & Gemini API integration
    ├── static/                 # Static assets (CSS styles & client-side JavaScript)
    │   ├── css/
    │   │   ├── ai_board.css    # Styles for AI Board UI
    │   │   └── index.css       # Styles for main layout and Virtual Draw UI
    │   └── ai_board.js         # Canvas rendering, toolbar events, and API fetch calls
    └── templates/              # HTML views
        ├── index.html          # Main page hosting the webcam Virtual Draw feed
        └── ai_board.html       # AI Board whiteboard interface
```

---

## 🛠️ Tech Stack

* **Backend:** Python, Flask
* **Computer Vision:** OpenCV, MediaPipe
* **Generative AI:** Google GenAI SDK (`gemini-2.0-flash`)
* **Frontend:** HTML5 Canvas, CSS3, JavaScript (ES6)

---

## ⚙️ Setup & Installation

### Prerequisites
* Python 3.8 or higher installed on your machine.
* A working webcam (required for the Virtual Draw gesture mode).
* A Google Gemini API Key. Get one from the [Google AI Studio](https://aistudio.google.com/).

### Installation Steps

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/pranav-kumar-080/Ai_Based_Air_Drawing_Learning_System.git
   cd Ai_Based_Air_Drawing_Learning_System
   ```
   *(Or navigate to your cloned repository folder)*

2. **Install Dependencies:**
   Install the required Python packages using pip:
   ```bash
   pip install flask opencv-python mediapipe numpy google-generativeai python-dotenv pillow
   ```

3. **Configure Environment Variables:**
   Create a file named `.env` in the `air_drawing` directory (or the root directory where you launch the application) and add your Google Gemini API key:
   ```env
   GOOGLE_API_KEY=your_actual_gemini_api_key_here
   ```

4. **Run the Application:**
   Navigate into the `air_drawing` directory and start the Flask development server:
   ```bash
   cd air_drawing
   python main.py
   ```

5. **Access the App:**
   Open your web browser and navigate to:
   [http://127.0.0.1:5000](http://127.0.0.1:5000)

---

## 💡 How to Use

### Virtual Draw Mode:
1. Click the **Start** button to turn on your webcam feed.
2. Hold up one hand. You will see MediaPipe skeleton tracking lines overlaying your hand.
3. Move your index finger to draw.
4. Pinch your thumb and index finger together to lift the pen and stop drawing.
5. Hover your index finger over the top menu headers to change colors or clear the canvas.
6. Once you've drawn a problem (e.g., `2 + 2 = ?`), click **Solve** to see the solution under *Recognition Result*.

### AI Board Mode:
1. Click **AI Board** in the navigation bar.
2. Select your brush size and color.
3. Draw or write your question on the canvas using your mouse or touchscreen.
4. Click **Solve Problem** to let the Gemini model analyze and display a structured step-by-step answer.
