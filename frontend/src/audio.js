/**
 * EchoAgent — Audio Capture, Visualizer, and Web Audio Player
 */
export class AudioManager {
    constructor() {
        this.audioContext = null;
        this.mediaStream = null;
        this.mediaRecorder = null;
        this.analyser = null;
        this.animationFrame = null;
    }

    async initMicrophone() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 16000,
            });
        }
        if (this.audioContext.state === "suspended") {
            await this.audioContext.resume();
        }

        this.mediaStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                channelCount: 1,
                sampleRate: 16000,
                echoCancellation: true,
                noiseSuppression: true,
            },
        });

        // Set up Analyser node for waveform visualizer
        const source = this.audioContext.createMediaStreamSource(this.mediaStream);
        this.analyser = this.audioContext.createAnalyser();
        this.analyser.fftSize = 256;
        source.connect(this.analyser);
    }

    startRecording(onChunkAvailable, intervalMs = 2000) {
        this.mediaRecorder = new MediaRecorder(this.mediaStream, {
            mimeType: "audio/webm;codecs=opus",
        });

        this.mediaRecorder.ondataavailable = async (event) => {
            if (event.data && event.data.size > 0) {
                const arrayBuffer = await event.data.arrayBuffer();
                onChunkAvailable(arrayBuffer);
            }
        };

        this.mediaRecorder.start(intervalMs);
    }

    stopRecording() {
        if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
            this.mediaRecorder.stop();
        }
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach((track) => track.stop());
        }
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
    }

    startVisualizer(canvasElement) {
        const canvasCtx = canvasElement.getContext("2d");
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);

        const draw = () => {
            this.animationFrame = requestAnimationFrame(draw);
            this.analyser.getByteFrequencyData(dataArray);

            canvasCtx.fillStyle = "rgb(15, 23, 42)";
            canvasCtx.fillRect(0, 0, canvasElement.width, canvasElement.height);

            const barWidth = (canvasElement.width / bufferLength) * 2.5;
            let barHeight;
            let x = 0;

            for (let i = 0; i < bufferLength; i++) {
                barHeight = (dataArray[i] / 255) * canvasElement.height * 0.8;
                // Gradient from indigo to purple
                canvasCtx.fillStyle = `rgb(${99 + barHeight}, ${102}, ${241})`;
                canvasCtx.fillRect(x, canvasElement.height - barHeight, barWidth, barHeight);
                x += barWidth + 1;
            }
        };

        draw();
    }

    async playWavBytes(arrayBuffer) {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
        const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer.slice(0));
        const source = this.audioContext.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(this.audioContext.destination);
        source.start(0);
    }
}

