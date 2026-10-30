/**
 * EchoAgent — Main Application Controller
 */
import { AudioManager } from "./audio.js";
import { CONFIG } from "./config.js";

class App {
    constructor() {
        this.audioManager = new AudioManager();
        this.currentSessionId = null;
        this.currentUserId = null;
        this.wsConverse = null;
        this.wsClone = null;
        this.sseEventSource = null;

        // UI Element References
        this.secIdle = document.getElementById("section-idle");
        this.secConversing = document.getElementById("section-conversing");
        this.secProcessing = document.getElementById("section-processing");
        this.secReady = document.getElementById("section-ready");
        this.secCloning = document.getElementById("section-cloning");

        this.btnStart = document.getElementById("btn-start");
        this.btnEndEarly = document.getElementById("btn-end-early");
        this.btnRecordAgain = document.getElementById("btn-record-again");
        this.btnSpeakToSelf = document.getElementById("btn-speak-to-self");
        this.btnExitClone = document.getElementById("btn-exit-clone");

        this.timerDisplay = document.getElementById("timer-display");
        this.transcriptText = document.getElementById("transcript-text");
        this.waveformCanvas = document.getElementById("waveform-canvas");

        this.progressBarFill = document.getElementById("progress-bar-fill");
        this.currentStepLabel = document.getElementById("current-step-label");
        this.percentLabel = document.getElementById("percent-label");
        this.stepCounter = document.getElementById("step-counter");
        this.clonedTranscript = document.getElementById("cloned-transcript");

        this.bindEvents();
    }

    bindEvents() {
        this.btnStart.addEventListener("click", () => this.startSession());
        this.btnEndEarly.addEventListener("click", () => this.endSessionEarly());
        this.btnRecordAgain.addEventListener("click", () => this.recordAgain());
        this.btnSpeakToSelf.addEventListener("click", () => this.startClonedSession());
        this.btnExitClone.addEventListener("click", () => this.exitClonedSession());
    }

    showSection(activeSec) {
        [this.secIdle, this.secConversing, this.secProcessing, this.secReady, this.secCloning].forEach((sec) => {
            sec.classList.add("hidden");
        });
        activeSec.classList.remove("hidden");
    }

    async startSession() {
        try {
            await this.audioManager.initMicrophone();

            // 1. Request session from API Gateway
            const res = await fetch(`${CONFIG.API_BASE}/api/v1/session`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ display_name: "User" }),
            });
            const session = await res.json();
            this.currentSessionId = session.session_id;

            this.showSection(this.secConversing);
            this.audioManager.startVisualizer(this.waveformCanvas);

            // 2. Connect to WebSocket
            this.wsConverse = new WebSocket(session.ws_url);
            this.wsConverse.binaryType = "arraybuffer";

            this.wsConverse.onmessage = (event) => {
                if (typeof event.data === "string") {
                    const msg = JSON.parse(event.data);
                    if (msg.type === "transcript") {
                        this.transcriptText.innerText = `"${msg.text}"`;
                    } else if (msg.type === "timer") {
                        const m = Math.floor(msg.remaining / 60).toString().padStart(2, "0");
                        const s = (msg.remaining % 60).toString().padStart(2, "0");
                        this.timerDisplay.innerText = `${m}:${s}`;
                    } else if (msg.type === "session_end") {
                        this.onSessionEnded();
                    }
                } else if (event.data instanceof ArrayBuffer) {
                    this.audioManager.playWavBytes(event.data);
                }
            };

            // 3. Start audio streaming chunks
            this.audioManager.startRecording((chunkBuffer) => {
                if (this.wsConverse && this.wsConverse.readyState === WebSocket.OPEN) {
                    this.wsConverse.send(chunkBuffer);
                }
            }, CONFIG.CHUNK_INTERVAL_MS);

        } catch (err) {
            alert(`Could not start session: ${err.message}`);
        }
    }

    endSessionEarly() {
        if (this.wsConverse && this.wsConverse.readyState === WebSocket.OPEN) {
            this.wsConverse.send(JSON.stringify({ type: "end" }));
        }
        this.onSessionEnded();
    }

    onSessionEnded() {
        this.audioManager.stopRecording();
        if (this.wsConverse) {
            this.wsConverse.close();
        }
        this.showSection(this.secProcessing);
        this.connectSSE();
    }

    connectSSE() {
        const sseUrl = `${CONFIG.API_BASE}/sse/status/${this.currentSessionId}`;
        this.sseEventSource = new EventSource(sseUrl);

        this.sseEventSource.addEventListener("progress", (e) => {
            const data = JSON.parse(e.data);
            this.updateProgressBar(data);
        });

        this.sseEventSource.addEventListener("complete", (e) => {
            this.sseEventSource.close();
            this.showSection(this.secReady);
        });

        this.sseEventSource.addEventListener("error", () => {
            this.sseEventSource.close();
        });
    }

    updateProgressBar(data) {
        const pct = Math.round(data.progress_percent || 0);
        this.progressBarFill.style.width = `${pct}%`;
        this.percentLabel.innerText = `${pct}%`;
        this.currentStepLabel.innerText = data.label || "Processing...";
        this.stepCounter.innerText = `Step ${data.step} of 5`;

        for (let i = 1; i <= 5; i++) {
            const stepEl = document.getElementById(`step-item-${i}`);
            if (i < data.step || (i === data.step && data.status === "completed")) {
                stepEl.classList.remove("text-slate-400");
                stepEl.classList.add("text-emerald-400");
                stepEl.querySelector(".step-icon").innerText = "✅";
            } else if (i === data.step) {
                stepEl.classList.remove("text-slate-400");
                stepEl.classList.add("text-indigo-400");
                stepEl.querySelector(".step-icon").innerText = "⚙️";
            }
        }
    }

    async startClonedSession() {
        this.showSection(this.secCloning);

        const wsUrl = `${CONFIG.WS_BASE}/ws/clone/${this.currentSessionId}`;
        this.wsClone = new WebSocket(wsUrl);
        this.wsClone.binaryType = "arraybuffer";

        this.wsClone.onmessage = (event) => {
            if (typeof event.data === "string") {
                const msg = JSON.parse(event.data);
                if (msg.type === "transcript") {
                    this.clonedTranscript.innerText = `"${msg.text}"`;
                }
            } else if (event.data instanceof ArrayBuffer) {
                this.audioManager.playWavBytes(event.data);
            }
        };
    }

    exitClonedSession() {
        if (this.wsClone) {
            this.wsClone.close();
        }
        this.showSection(this.secReady);
    }

    async recordAgain() {
        this.showSection(this.secIdle);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    new App();
});

