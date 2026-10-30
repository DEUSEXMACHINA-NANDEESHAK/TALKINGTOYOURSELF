/**
 * EchoAgent — Frontend Configuration
 */
export const CONFIG = {
    API_BASE: window.location.origin.includes("localhost")
        ? "http://localhost:8000"
        : window.location.origin,
    WS_BASE: window.location.origin.includes("localhost")
        ? "ws://localhost:8000"
        : window.location.origin.replace(/^http/, "ws"),
    SAMPLE_RATE: 16000,
    CHUNK_INTERVAL_MS: 2000,
    MAX_DURATION_SECONDS: 120,
};

