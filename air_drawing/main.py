
import io
import os
import time
import threading

import cv2
import mediapipe as mp
import numpy as np
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request
from PIL import Image
import google.generativeai as genai
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision


# ==================================================
# Configuration
# ==================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "models", "hand_landmarker.task")

load_dotenv(os.path.join(BASE_DIR, ".env"))
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

app = Flask(__name__)

CANVAS_WIDTH = 640
CANVAS_HEIGHT = 480
COOLDOWN_SECONDS = 0.7
CAMERA_INDEX = 0

model = None

if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-3.6-flash")

if not os.path.isfile(MODEL_PATH):
    raise FileNotFoundError(
        f"MediaPipe model not found: {MODEL_PATH}"
    )

base_options = mp_python.BaseOptions(
    model_asset_path=MODEL_PATH
)

hand_options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=1,
    min_hand_detection_confidence=0.7,
    min_hand_presence_confidence=0.5,
    min_tracking_confidence=0.5,
)

hand_landmarker = vision.HandLandmarker.create_from_options(
    hand_options
)


# ==================================================
# Shared state
# ==================================================

state_lock = threading.RLock()
camera_lock = threading.Lock()

camera = None
camera_stream_active = False
last_frame_timestamp_ms = 0
last_jpeg = None

current_canvas = np.full(
    (CANVAS_HEIGHT, CANVAS_WIDTH, 3),
    255,
    dtype=np.uint8,
)

strokes = []
current_stroke = []

frozen = False
generation_status = "idle"
generation_answer = ""
generation_error = ""
generation_id = 0

last_action = ""
last_action_at = 0.0
last_action_message = ""

gesture_candidate = None
gesture_since = 0.0
gesture_latched = False


# ==================================================
# Camera management
# ==================================================

def get_camera():
    global camera

    with camera_lock:
        if camera is None or not camera.isOpened():
            candidate = cv2.VideoCapture(CAMERA_INDEX)

            if not candidate.isOpened():
                candidate.release()
                raise RuntimeError(
                    "Could not open the webcam. Check camera permissions "
                    "and make sure another application is not using it."
                )

            candidate.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            candidate.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            candidate.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            camera = candidate

        return camera


def release_camera(expected_camera=None):
    global camera

    with camera_lock:
        if camera is None:
            return

        if expected_camera is not None and camera is not expected_camera:
            return

        camera.release()
        camera = None


# ==================================================
# Canvas and strokes
# ==================================================

def redraw_canvas():
    global current_canvas

    canvas = np.full(
        (CANVAS_HEIGHT, CANVAS_WIDTH, 3),
        255,
        dtype=np.uint8,
    )

    for stroke in strokes:
        if not stroke:
            continue

        if len(stroke) == 1:
            cv2.circle(
                canvas,
                stroke[0],
                3,
                (0, 0, 0),
                -1,
                cv2.LINE_AA,
            )

        for start, end in zip(stroke, stroke[1:]):
            cv2.line(
                canvas,
                start,
                end,
                (0, 0, 0),
                5,
                cv2.LINE_AA,
            )

    current_canvas = canvas


def reset_drawing():
    global strokes, current_stroke, last_action_message

    with state_lock:
        strokes = []
        current_stroke = []
        redraw_canvas()
        last_action_message = "Canvas reset"


def undo_stroke():
    global current_stroke, last_action_message

    with state_lock:
        if current_stroke:
            if strokes and strokes[-1] is current_stroke:
                strokes.pop()

            current_stroke = []

        elif strokes:
            strokes.pop()

        redraw_canvas()
        last_action_message = "Last stroke undone"


def add_canvas_point(point):
    global current_stroke

    with state_lock:
        if frozen:
            return

        if not current_stroke:
            current_stroke = [point]
            strokes.append(current_stroke)
        else:
            previous = current_stroke[-1]

            distance = np.hypot(
                point[0] - previous[0],
                point[1] - previous[1],
            )

            if distance < 100:
                current_stroke.append(point)
            else:
                current_stroke = [point]
                strokes.append(current_stroke)

        redraw_canvas()


# ==================================================
# Gesture recognition
# ==================================================

def finger_states(landmarks):
    """
    Returns extension states for index, middle, ring and pinky,
    plus an approximate thumb-extension state.

    Keep the palm facing the camera and the hand reasonably upright.
    """

    extended = [
        landmarks[8].y < landmarks[6].y,      # Index
        landmarks[12].y < landmarks[10].y,    # Middle
        landmarks[16].y < landmarks[14].y,    # Ring
        landmarks[20].y < landmarks[18].y,    # Pinky
    ]

    thumb_extended = (
        abs(landmarks[4].x - landmarks[2].x) > 0.055
    )

    return extended, thumb_extended


def classify_gesture(landmarks):
    extended, thumb_extended = finger_states(landmarks)
    count = sum(extended)

    # Whole open palm: submit.
    if count == 4 and thumb_extended:
        return "submit"

    # Thumb extended, all four other fingers folded: reset.
    if count == 0 and thumb_extended:
        return "reset"

    # Exactly three fingers: undo.
    if count == 3 and not thumb_extended:
        return "undo"

    # Exactly one finger: draw with that finger.
    if count == 1 and not thumb_extended:
        return "draw"

    return None


def reset_gesture_tracking():
    global gesture_candidate, gesture_since, gesture_latched

    gesture_candidate = None
    gesture_since = 0.0
    gesture_latched = False


# ==================================================
# Gemini
# ==================================================

MATH_PROMPT = """
You are Junior, a concise, patient mathematics tutor.

Read the handwritten mathematical problem in the supplied image.
Transcribe it and solve it accurately.

Use Markdown headings and numbered steps when useful.
Use LaTeX for equations, with \\( ... \\) for inline mathematics
and \\[ ... \\] for display mathematics.

For simple arithmetic, keep the explanation short.
Do not invent unclear symbols.
If the drawing is unclear, explain what you can read and ask the user
to redraw the problem.

Always finish with a clearly labelled **Final answer**.
"""


def solve_image(image_bytes, mime_type="image/png"):
    if model is None:
        raise RuntimeError(
            "GOOGLE_API_KEY is missing. Check your existing .env file."
        )

    response = model.generate_content(
        [
            MATH_PROMPT,
            {
                "mime_type": mime_type,
                "data": image_bytes,
            },
        ]
    )

    answer = getattr(response, "text", None)

    if not answer:
        raise RuntimeError(
            "Gemini returned an empty response. Please try again."
        )

    return answer.strip()


# ==================================================
# Generation lifecycle
# ==================================================

def begin_generation(image_bytes, this_generation_id):
    global generation_status
    global generation_answer, generation_error, frozen

    try:
        answer = solve_image(image_bytes)

        with state_lock:
            # Ignore responses from an older or paused generation.
            if this_generation_id != generation_id:
                return

            if generation_status != "generating":
                return

            # Keep the answer visible while resetting the drawing.
            generation_answer = answer
            generation_error = ""
            generation_status = "done"

            reset_drawing()
            frozen = False
            reset_gesture_tracking()

    except Exception as error:
        app.logger.exception("Gemini generation failed")

        with state_lock:
            if this_generation_id != generation_id:
                return

            if generation_status != "generating":
                return

            generation_error = str(error)
            generation_status = "error"

            # Keep the submitted drawing frozen so it is not lost.
            frozen = True


def submit_drawing():
    global frozen
    global generation_status, generation_answer
    global generation_error, generation_id, last_action_message

    with state_lock:
        if frozen or generation_status == "generating":
            return

        if not strokes:
            last_action_message = "Draw something before submitting"
            return

        success, encoded = cv2.imencode(".png", current_canvas)

        if not success:
            generation_status = "error"
            generation_error = "Could not capture the drawing."
            frozen = True
            return

        image_bytes = encoded.tobytes()

        generation_id += 1
        this_generation_id = generation_id

        frozen = True
        generation_status = "generating"
        generation_answer = ""
        generation_error = ""
        last_action_message = "Drawing submitted"

    threading.Thread(
        target=begin_generation,
        args=(image_bytes, this_generation_id),
        daemon=True,
    ).start()


# ==================================================
# Stable gesture actions
# ==================================================

def process_gesture(gesture):
    global gesture_candidate, gesture_since, gesture_latched
    global last_action, last_action_at
    global frozen, generation_status
    global generation_answer, generation_error, generation_id

    now = time.monotonic()

    with state_lock:
        if gesture is None:
            reset_gesture_tracking()
            return

        if gesture != gesture_candidate:
            gesture_candidate = gesture
            gesture_since = now
            gesture_latched = False
            return

        # A held gesture must not trigger repeatedly.
        if gesture_latched:
            return

        if now - gesture_since < COOLDOWN_SECONDS:
            return

        if now - last_action_at < COOLDOWN_SECONDS:
            return

        if gesture == "submit":
            if not frozen:
                submit_drawing()

        elif gesture == "reset":
            if not frozen:
                generation_id += 1
                generation_status = "idle"
                generation_answer = ""
                generation_error = ""
                reset_drawing()

        elif gesture == "undo":
            if not frozen:
                undo_stroke()

        # Drawing itself is continuous and handled in the camera loop.
        gesture_latched = True
        last_action = gesture
        last_action_at = now


# ==================================================
# Camera stream
# ==================================================

def generate_frames():
    global last_frame_timestamp_ms, last_jpeg
    global current_stroke, camera_stream_active

    active_camera = get_camera()

    with state_lock:
        camera_stream_active = True

    try:
        while True:
            with state_lock:
                is_frozen = frozen
                saved_jpeg = last_jpeg

            # Freeze the visible camera frame while solving.
            if is_frozen and saved_jpeg is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + saved_jpeg
                    + b"\r\n"
                )
                time.sleep(0.05)
                continue

            # Stop this stream if the camera was replaced or switched off.
            with camera_lock:
                if camera is not active_camera:
                    break

            ret, frame = active_camera.read()

            if not ret:
                time.sleep(0.03)
                continue

            frame = cv2.flip(frame, 1)

            height, width = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=rgb,
            )

            timestamp_ms = max(
                int(time.monotonic() * 1000),
                last_frame_timestamp_ms + 1,
            )
            last_frame_timestamp_ms = timestamp_ms

            result = hand_landmarker.detect_for_video(
                mp_image,
                timestamp_ms,
            )

            gesture = None

            if result.hand_landmarks:
                landmarks = result.hand_landmarks[0]
                gesture = classify_gesture(landmarks)

                points = [
                    (int(lm.x * width), int(lm.y * height))
                    for lm in landmarks
                ]

                process_gesture(gesture)

                with state_lock:
                    can_draw = (
                        not frozen
                        and gesture == "draw"
                    )

                if can_draw:
                    extended, _ = finger_states(landmarks)

                    # Use whichever single finger is extended.
                    active_finger = extended.index(True)
                    fingertip_indices = [8, 12, 16, 20]
                    fingertip = points[
                        fingertip_indices[active_finger]
                    ]

                    canvas_point = (
                        max(
                            0,
                            min(
                                CANVAS_WIDTH - 1,
                                int(
                                    fingertip[0]
                                    * CANVAS_WIDTH
                                    / width
                                ),
                            ),
                        ),
                        max(
                            0,
                            min(
                                CANVAS_HEIGHT - 1,
                                int(
                                    fingertip[1]
                                    * CANVAS_HEIGHT
                                    / height
                                ),
                            ),
                        ),
                    )

                    add_canvas_point(canvas_point)
                else:
                    with state_lock:
                        current_stroke = []

            else:
                with state_lock:
                    current_stroke = []

                process_gesture(None)

            with state_lock:
                visible_strokes = [
                    list(stroke) for stroke in strokes
                ]
                status = generation_status

            # Overlay the black strokes on the mirrored camera.
            for stroke in visible_strokes:
                if len(stroke) == 1:
                    point = (
                        int(stroke[0][0] * width / CANVAS_WIDTH),
                        int(stroke[0][1] * height / CANVAS_HEIGHT),
                    )

                    cv2.circle(
                        frame,
                        point,
                        3,
                        (0, 0, 0),
                        -1,
                        cv2.LINE_AA,
                    )

                for start, end in zip(stroke, stroke[1:]):
                    camera_start = (
                        int(start[0] * width / CANVAS_WIDTH),
                        int(start[1] * height / CANVAS_HEIGHT),
                    )

                    camera_end = (
                        int(end[0] * width / CANVAS_WIDTH),
                        int(end[1] * height / CANVAS_HEIGHT),
                    )

                    cv2.line(
                        frame,
                        camera_start,
                        camera_end,
                        (0, 0, 0),
                        5,
                        cv2.LINE_AA,
                    )

            if status == "generating":
                cv2.putText(
                    frame,
                    "JUNIOR IS THINKING...",
                    (24, height - 28),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (255, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

            success, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), 88],
            )

            if not success:
                continue

            frame_bytes = buffer.tobytes()

            with state_lock:
                last_jpeg = frame_bytes

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n"
                + frame_bytes
                + b"\r\n"
            )

    except GeneratorExit:
        pass

    except Exception:
        app.logger.exception("Camera stream failed")

    finally:
        with state_lock:
            camera_stream_active = False

        release_camera(active_camera)


# ==================================================
# Routes
# ==================================================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/ai_board")
def ai_board():
    return render_template("ai_board.html")


@app.route("/video_feed")
def video_feed():
    try:
        return Response(
            generate_frames(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except RuntimeError as error:
        return jsonify({"error": str(error)}), 500


@app.route("/state")
def get_state():
    with state_lock:
        return jsonify({
            "frozen": frozen,
            "status": generation_status,
            "answer": generation_answer,
            "error": generation_error,
            "last_action": last_action,
            "message": last_action_message,
        })


@app.route("/camera/off", methods=["POST"])
def camera_off():
    release_camera()

    with state_lock:
        reset_gesture_tracking()
        current_stroke = None

    return jsonify({"status": "off"})


@app.route("/reset", methods=["POST"])
def reset_route():
    global frozen, generation_status
    global generation_answer, generation_error, generation_id

    with state_lock:
        generation_id += 1
        frozen = False
        generation_status = "idle"
        generation_answer = ""
        generation_error = ""
        reset_drawing()
        reset_gesture_tracking()

    return jsonify({"status": "success"})


@app.route("/undo", methods=["POST"])
def undo_route():
    with state_lock:
        if not frozen:
            undo_stroke()

    return jsonify({"status": "success"})


@app.route("/pause_generation", methods=["POST"])
def pause_generation():
    global generation_id, generation_status
    global generation_error, frozen, last_action_message

    with state_lock:
        if generation_status == "generating":
            # Invalidate the pending response. The remote request may
            # continue, but its eventual result will be ignored.
            generation_id += 1
            generation_status = "paused"
            generation_error = ""
            frozen = False
            last_action_message = "Generation paused"
            reset_gesture_tracking()

    return jsonify({
        "status": generation_status,
        "note": "A late Gemini response will be ignored.",
    })


@app.route("/analyze_canvas", methods=["GET", "POST"])
def analyze_canvas():
    try:
        with state_lock:
            success, encoded = cv2.imencode(
                ".png",
                current_canvas,
            )

            if not success:
                return jsonify({
                    "error": "Could not encode canvas.",
                    "status": "error",
                }), 500

            image_bytes = encoded.tobytes()

        answer = solve_image(image_bytes)

        return jsonify({
            "response": answer,
            "status": "success",
        })

    except Exception as error:
        app.logger.exception("Canvas analysis failed")

        return jsonify({
            "error": str(error),
            "status": "error",
        }), 500


@app.route("/solve", methods=["POST"])
def solve():
    if "image" not in request.files:
        return jsonify({
            "error": "No image was provided.",
            "status": "error",
        }), 400

    try:
        image = Image.open(
            request.files["image"]
        ).convert("RGB")

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")

        answer = solve_image(buffer.getvalue())

        return jsonify({
            "result": answer,
            "status": "success",
        })

    except Exception as error:
        app.logger.exception("Image solving failed")

        return jsonify({
            "error": str(error),
            "status": "error",
        }), 500


# ==================================================
# Startup and cleanup
# ==================================================

if __name__ == "__main__":
    try:
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            threaded=True,
            use_reloader=False,
        )

    finally:
        release_camera()
        hand_landmarker.close()
