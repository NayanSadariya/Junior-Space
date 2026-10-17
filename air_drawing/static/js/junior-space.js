
(() => {
    "use strict";

    const $ = (id) => document.getElementById(id);

    const cameraFeed = $("cameraFeed");
    const cameraPlaceholder = $("cameraPlaceholder");
    const cameraToggleButton = $("cameraToggleButton");
    const enableCameraButton = $("enableCameraButton");
    const cameraStatus = $("cameraStatus");
    const cameraMessage = $("cameraMessage");

    const answerContent = $("answerContent");
    const answerStatus = $("answerStatus");
    const generationFooter = $("generationFooter");
    const generationMessage = $("generationMessage");
    const pauseGenerationButton = $("pauseGenerationButton");
    const toast = $("toast");

    let cameraOn = false;
    let cameraStarting = false;
    let pollingTimer = null;
    let toastTimer = null;
    let lastAnswer = "";
    let lastStatus = "idle";
    let lastMessage = "";
    let lastPauseToastStatus = "";
    let tabWasHidden = false;

    const CAMERA_ICON = `
        <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="6" width="13" height="12" rx="3"></rect>
            <path d="m16 10 5-3v10l-5-3"></path>
        </svg>
    `;

    function showToast(message) {
        toast.textContent = message;
        toast.classList.add("visible");

        window.clearTimeout(toastTimer);

        toastTimer = window.setTimeout(() => {
            toast.classList.remove("visible");
        }, 2600);
    }

    function setCameraUI(enabled) {
        cameraOn = enabled;

        cameraPlaceholder.hidden = enabled;
        cameraFeed.classList.toggle("visible", enabled);
        cameraStatus.classList.toggle("is-on", enabled);

        cameraStatus.innerHTML = `
            <span class="status-dot"></span>
            ${enabled ? "Camera on" : "Camera off"}
        `;

        cameraToggleButton.setAttribute(
            "aria-label",
            enabled ? "Turn camera off" : "Turn camera on"
        );

        cameraToggleButton.title = enabled
            ? "Turn camera off"
            : "Turn camera on";

        cameraToggleButton.innerHTML = CAMERA_ICON;
        cameraToggleButton.classList.toggle("active", enabled);
    }

    function startPolling() {
        stopPolling();
        pollState();
        pollingTimer = window.setInterval(pollState, 600);
    }

    function stopPolling() {
        if (pollingTimer !== null) {
            window.clearInterval(pollingTimer);
            pollingTimer = null;
        }
    }

    async function startCamera() {
        if (cameraOn || cameraStarting) return;

        cameraStarting = true;

        cameraMessage.textContent = "Connecting to camera…";
        cameraMessage.classList.add("visible");

        cameraFeed.onload = () => {
            cameraMessage.textContent = "";
            cameraMessage.classList.remove("visible");
        };

        cameraFeed.onerror = () => {
            setCameraUI(false);
            stopPolling();

            cameraFeed.removeAttribute("src");
            cameraMessage.textContent = "";
            cameraMessage.classList.remove("visible");

            fetch("/camera/off", {
                method: "POST",
                keepalive: true
            }).catch(() => {});

            showToast("Could not connect to the camera.");
        };

        // The image element owns the single MJPEG stream.
        cameraFeed.src = `/video_feed?t=${Date.now()}`;
        setCameraUI(true);
        startPolling();

        cameraStarting = false;
    }

    async function stopCamera({ silent = false } = {}) {
        if (!cameraOn && !cameraFeed.getAttribute("src")) return;

        setCameraUI(false);
        stopPolling();

        // Removing the source closes the browser's MJPEG connection.
        cameraFeed.removeAttribute("src");

        try {
            await fetch("/camera/off", {
                method: "POST",
                keepalive: true
            });
        } catch (_) {
            // The page may already be closing.
        }

        if (!silent) {
            showToast("Camera turned off.");
        }
    }

    async function pollState() {
        if (!cameraOn || document.hidden) return;

        try {
            const response = await fetch(`/state?t=${Date.now()}`, {
                cache: "no-store"
            });

            if (!response.ok) return;

            const state = await response.json();
            updateUI(state);
        } catch (_) {
            // Retry on the next polling interval.
        }
    }

    function setAnswerStatus(status, label) {
        answerStatus.className = "answer-status";

        if (status) {
            answerStatus.classList.add(`status-${status}`);
        }

        const dot = document.createElement("span");
        dot.className = "status-dot";

        answerStatus.replaceChildren(
            dot,
            document.createTextNode(label)
        );
    }

    function escapeHTML(value) {
        return String(value).replace(/[&<>"']/g, (character) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }

    function renderAnswer(markdown) {
        if (!markdown) {
            showEmptyAnswer();
            return;
        }

        let html;

        if (window.marked) {
            html = window.marked.parse(markdown);
        } else {
            html = `<p>${escapeHTML(markdown).replace(/\n/g, "<br>")}</p>`;
        }

        if (window.DOMPurify) {
            html = window.DOMPurify.sanitize(html);
        } else {
            // Safe fallback: display plain text instead of unsanitized HTML.
            html = `<p>${escapeHTML(markdown).replace(/\n/g, "<br>")}</p>`;
        }

        answerContent.innerHTML = html;

        if (
            window.MathJax &&
            typeof window.MathJax.typesetPromise === "function"
        ) {
            window.MathJax.typesetPromise([answerContent]).catch(() => {});
        }
    }

    function showEmptyAnswer() {
        answerContent.innerHTML = `
            <div class="empty-answer">
                <div class="answer-sparkle">✳</div>
                <h3>Let's solve something.</h3>
                <p>
                    Draw a maths problem in the air, then show your open
                    palm to send it to Junior.
                </p>
            </div>
        `;
    }

    function showLoadingAnswer() {
        answerContent.innerHTML = `
            <div class="loading-answer">
                <div class="loading-orb">✳</div>
                <h3>Working it out</h3>
                <p>Reading your drawing and preparing a solution.</p>
            </div>
        `;
    }

    function showErrorAnswer(error) {
        answerContent.innerHTML = `
            <div class="error-answer">
                <div class="answer-sparkle">!</div>
                <h3>Couldn't solve that yet.</h3>
                <p>${escapeHTML(error || "An unexpected error occurred.")}</p>
                <p>Your drawing has been kept. You can try again.</p>
            </div>
        `;
    }

    function showPausedAnswer() {
        answerContent.innerHTML = `
            <div class="empty-answer">
                <div class="answer-sparkle">Ⅱ</div>
                <h3>Generation paused</h3>
                <p>
                    You can continue drawing now. Show your open palm when
                    you're ready to submit another problem.
                </p>
            </div>
        `;
    }

    function updateUI(state) {
        const status = state.status || "idle";
        const answer = state.answer || "";
        const error = state.error || "";
        const message = state.message || "";

        if (status === "generating") {
            setAnswerStatus("generating", "Thinking");

            generationFooter.hidden = false;
            generationMessage.textContent = "Junior is thinking…";
            pauseGenerationButton.disabled = false;
            pauseGenerationButton.textContent = "Pause";

            if (lastStatus !== "generating") {
                showLoadingAnswer();
            }
        } else if (status === "done") {
            setAnswerStatus("done", "Answered");
            generationFooter.hidden = true;

            // The canvas resets on the server, but the answer remains visible.
            if (answer && answer !== lastAnswer) {
                renderAnswer(answer);
                lastAnswer = answer;
            }
        } else if (status === "error") {
            setAnswerStatus("error", "Something went wrong");
            generationFooter.hidden = true;

            if (lastStatus !== "error") {
                showErrorAnswer(error);
            }
        } else if (status === "paused") {
            setAnswerStatus("paused", "Paused");
            generationFooter.hidden = true;

            if (lastPauseToastStatus !== status) {
                showPausedAnswer();
                showToast("Generation paused.");
                lastPauseToastStatus = status;
            }
        } else {
            setAnswerStatus("", "Ready");
            generationFooter.hidden = true;

            // A manual thumb reset clears the previous answer.
            // A successful generation uses status "done", so it is preserved.
            if (
                message === "Canvas reset" &&
                lastStatus !== "idle" &&
                lastStatus !== "done"
            ) {
                lastAnswer = "";
                showEmptyAnswer();
            }
        }

        if (message && message !== lastMessage) {
            if (
                message === "Last stroke undone" ||
                message === "Canvas reset" ||
                message === "Draw something before submitting"
            ) {
                showToast(message);
            }

            lastMessage = message;
        }

        if (status !== "paused") {
            lastPauseToastStatus = "";
        }

        lastStatus = status;
    }

    async function pauseGeneration() {
        pauseGenerationButton.disabled = true;
        pauseGenerationButton.textContent = "Pausing…";

        try {
            const response = await fetch("/pause_generation", {
                method: "POST"
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.error || "Could not pause generation."
                );
            }

            generationFooter.hidden = true;
            setAnswerStatus("paused", "Paused");
            showPausedAnswer();

            lastAnswer = "";
            lastStatus = "paused";
            lastPauseToastStatus = "paused";

            showToast("Generation paused. You can draw again.");
        } catch (error) {
            showToast(error.message || "Could not pause generation.");
        } finally {
            pauseGenerationButton.disabled = false;
            pauseGenerationButton.textContent = "Pause";
        }
    }

    cameraToggleButton.addEventListener("click", () => {
        if (cameraOn) {
            stopCamera();
        } else {
            startCamera();
        }
    });

    enableCameraButton.addEventListener("click", startCamera);
    pauseGenerationButton.addEventListener("click", pauseGeneration);

    document.addEventListener("visibilitychange", () => {
        if (document.hidden) {
            tabWasHidden = cameraOn;

            if (cameraOn) {
                stopCamera({ silent: true });
            }
        } else if (tabWasHidden) {
            tabWasHidden = false;
            showToast("Camera is off. Turn it on when you're ready.");
        }
    });

    window.addEventListener("pagehide", () => {
        stopPolling();

        if (cameraOn) {
            fetch("/camera/off", {
                method: "POST",
                keepalive: true
            }).catch(() => {});
        }
    });

    // Initial UI state.
    setCameraUI(false);
    showEmptyAnswer();
    setAnswerStatus("", "Ready");
})();
