"""
Breath Sensor — Real-time microphone breath detection.

Captures audio from the default microphone, extracts the respiratory
envelope (0.1-0.5 Hz), and pushes oscillating breath signals to the
coherence engine via the bloom relay's /samples endpoint at 10 Hz.

The respiratory rhythm naturally maps to the engine's ULTRA phi-band
(center = phi^-2 = 0.382 Hz), providing REAL biometric coherence data.

Usage:
  python breath_sensor.py [--port 7777] [--token TOKEN] [--device INDEX]

Requires: sounddevice, scipy, numpy
"""

import sys
import os
import json
import time
import signal
import argparse
import logging
import threading
import numpy as np
from collections import deque
from urllib.request import Request, urlopen
from urllib.error import URLError

try:
    import sounddevice as sd
except ImportError:
    print('ERROR: sounddevice not installed. Run: pip install sounddevice', file=sys.stderr)
    sys.exit(1)

from scipy.signal import butter, sosfilt, hilbert, find_peaks

logging.basicConfig(
    level=logging.INFO,
    format='[breath-sensor] %(levelname)s %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger('breath-sensor')

# --- Constants ---
AUDIO_SAMPLE_RATE = 44100       # Standard audio capture rate
AUDIO_BLOCK_SIZE = 2048         # ~46ms chunks
OUTPUT_SAMPLE_RATE = 10.0       # Push to engine at 10 Hz
ENVELOPE_WINDOW_S = 10.0        # Rolling window for envelope (seconds)
PUSH_INTERVAL_S = 1.0           # Push every 1 second

# Breath sound frequency range (acoustic)
BREATH_ACOUSTIC_LOW = 100.0     # Hz
BREATH_ACOUSTIC_HIGH = 1500.0   # Hz

# Respiratory rhythm range
RESPIRATORY_LOW = 0.1           # Hz (6 breaths/min)
RESPIRATORY_HIGH = 0.5          # Hz (30 breaths/min)


class BreathSensor:
    """Real-time breath detection from microphone audio."""

    def __init__(self, relay_port: int = 7777, relay_token: str = '',
                 device: int = None):
        self.relay_url = f'http://localhost:{relay_port}/samples'
        self.relay_token = relay_token
        self.device = device
        self._running = False
        self._lock = threading.Lock()

        # Audio buffer — stores raw envelope values at ~AUDIO_SAMPLE_RATE/AUDIO_BLOCK_SIZE Hz
        # That's ~21 Hz update rate
        envelope_buf_size = int(ENVELOPE_WINDOW_S * AUDIO_SAMPLE_RATE / AUDIO_BLOCK_SIZE) * 2
        self._envelope_buf = deque(maxlen=envelope_buf_size)

        # Output buffer — resampled to OUTPUT_SAMPLE_RATE
        output_buf_size = int(ENVELOPE_WINDOW_S * OUTPUT_SAMPLE_RATE)
        self._output_buf = deque(maxlen=output_buf_size)

        # Breath acoustic bandpass filter (isolate breath sounds from speech/noise)
        self._sos_acoustic = butter(
            4, [BREATH_ACOUSTIC_LOW, BREATH_ACOUSTIC_HIGH],
            'bandpass', fs=AUDIO_SAMPLE_RATE, output='sos'
        )

        # Respiratory rhythm bandpass (extract breathing oscillation from envelope)
        # Applied at the envelope rate (~21 Hz)
        envelope_rate = AUDIO_SAMPLE_RATE / AUDIO_BLOCK_SIZE
        self._sos_respiratory = butter(
            3, [RESPIRATORY_LOW, RESPIRATORY_HIGH],
            'bandpass', fs=envelope_rate, output='sos'
        )

        # Filter states for streaming (maintained between chunks)
        self._acoustic_zi = None
        self._respiratory_zi = None

        # Stats
        self._push_count = 0
        self._last_breath_rate = 0.0
        self._last_phase = 0.0

    def _audio_callback(self, indata, frames, time_info, status):
        """Called by sounddevice for each audio block."""
        if status:
            log.debug(f'Audio status: {status}')

        # Mono signal
        audio = indata[:, 0].copy()

        # Bandpass to breath acoustic range (100-1500 Hz)
        if self._acoustic_zi is None:
            # Initialize filter state
            from scipy.signal import sosfilt_zi
            self._acoustic_zi = sosfilt_zi(self._sos_acoustic) * audio[0]

        breath_audio, self._acoustic_zi = sosfilt(
            self._sos_acoustic, audio, zi=self._acoustic_zi
        )

        # RMS energy of filtered audio — this is the breath envelope
        rms = np.sqrt(np.mean(breath_audio ** 2))

        with self._lock:
            self._envelope_buf.append(rms)

    def _process_and_push(self):
        """Process envelope buffer and push respiratory signal to relay."""
        with self._lock:
            if len(self._envelope_buf) < 20:
                return  # Not enough data yet
            envelope = np.array(self._envelope_buf)

        # Apply respiratory bandpass to extract breathing rhythm
        if len(envelope) < 15:
            return

        try:
            respiratory = sosfilt(self._sos_respiratory, envelope)
        except ValueError:
            return

        # Normalize to [-1, 1] range
        max_val = np.max(np.abs(respiratory))
        if max_val > 1e-10:
            respiratory = respiratory / max_val

        # Resample to OUTPUT_SAMPLE_RATE (10 Hz)
        # envelope is at ~21 Hz, we want 10 Hz
        envelope_rate = AUDIO_SAMPLE_RATE / AUDIO_BLOCK_SIZE
        n_output = int(len(respiratory) * OUTPUT_SAMPLE_RATE / envelope_rate)
        if n_output < 2:
            return

        indices = np.linspace(0, len(respiratory) - 1, n_output)
        resampled = np.interp(indices, np.arange(len(respiratory)), respiratory)

        # Take the last 1 second (10 samples at 10 Hz)
        n_push = int(OUTPUT_SAMPLE_RATE * PUSH_INTERVAL_S)
        samples = resampled[-n_push:].tolist()

        # Extract breath metrics for logging
        try:
            peaks, _ = find_peaks(respiratory, distance=int(envelope_rate * 1.5))
            if len(peaks) >= 2:
                avg_period = np.mean(np.diff(peaks)) / envelope_rate
                self._last_breath_rate = 1.0 / avg_period if avg_period > 0 else 0
            # Phase from Hilbert transform on last segment
            if len(respiratory) > 20:
                analytic = hilbert(respiratory[-int(envelope_rate * 5):])
                phase = np.angle(analytic[-1])
                self._last_phase = (phase % (2 * np.pi)) / (2 * np.pi)
        except Exception:
            pass

        # Push to relay
        self._push_samples('breath', samples, OUTPUT_SAMPLE_RATE)

    def _push_samples(self, stream_name: str, samples: list, sample_rate: float):
        """Push samples to the bloom relay /samples endpoint."""
        payload = json.dumps({
            'stream': stream_name,
            'samples': samples,
            'sample_rate': sample_rate,
            'source': 'microphone',
        }).encode('utf-8')

        req = Request(self.relay_url, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        if self.relay_token:
            req.add_header('Authorization', f'Bearer {self.relay_token}')

        try:
            with urlopen(req, timeout=2) as resp:
                self._push_count += 1
                if self._push_count % 10 == 0:
                    result = json.loads(resp.read())
                    coherence = result.get('scalarCoherence', 0)
                    log.info(
                        f'Push #{self._push_count}: breath={self._last_breath_rate:.2f}Hz '
                        f'({self._last_breath_rate*60:.0f}BPM) phase={self._last_phase:.2f} '
                        f'coherence={coherence:.3f}'
                    )
        except URLError as e:
            if self._push_count == 0:
                log.error(f'Cannot reach relay at {self.relay_url}: {e}')
            # Silent after first error — relay might be offline temporarily
        except Exception as e:
            log.debug(f'Push error: {e}')

    def start(self):
        """Start capturing and processing."""
        self._running = True

        # List available devices
        try:
            devices = sd.query_devices()
            default_in = sd.default.device[0]
            dev = self.device if self.device is not None else default_in
            dev_info = sd.query_devices(dev)
            log.info(f'Using microphone: {dev_info["name"]} (device {dev})')
        except Exception as e:
            log.error(f'No audio input device: {e}')
            return

        # Start audio stream
        try:
            self._stream = sd.InputStream(
                device=dev,
                channels=1,
                samplerate=AUDIO_SAMPLE_RATE,
                blocksize=AUDIO_BLOCK_SIZE,
                callback=self._audio_callback,
            )
            self._stream.start()
            log.info(f'Audio capture started at {AUDIO_SAMPLE_RATE}Hz, block={AUDIO_BLOCK_SIZE}')
        except Exception as e:
            log.error(f'Failed to start audio stream: {e}')
            return

        # Processing loop
        log.info(f'Breath sensor active. Pushing to {self.relay_url} every {PUSH_INTERVAL_S}s')
        try:
            while self._running:
                time.sleep(PUSH_INTERVAL_S)
                self._process_and_push()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def stop(self):
        """Stop capturing."""
        self._running = False
        if hasattr(self, '_stream'):
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
        log.info(f'Breath sensor stopped. Total pushes: {self._push_count}')


def main():
    parser = argparse.ArgumentParser(description='Real-time breath detection sensor')
    parser.add_argument('--port', type=int, default=7777, help='Bloom relay port')
    parser.add_argument('--token', type=str, default='', help='Relay auth token')
    parser.add_argument('--device', type=int, default=None, help='Audio device index')
    parser.add_argument('--list-devices', action='store_true', help='List audio devices and exit')
    args = parser.parse_args()

    if args.list_devices:
        print(sd.query_devices())
        return

    # Also check env vars
    token = args.token or os.environ.get('BLOOM_RELAY_TOKEN', '')

    sensor = BreathSensor(
        relay_port=args.port,
        relay_token=token,
        device=args.device,
    )

    # Graceful shutdown
    def handle_signal(sig, frame):
        sensor.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    sensor.start()


if __name__ == '__main__':
    main()
