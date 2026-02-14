"""
PPG Sensor — Camera-based photoplethysmography for heart rate / HRV.

Captures video from the webcam and extracts pulse signals using two modes:

  1. Finger-on-camera mode: When a finger covers the lens, extracts PPG from
     the red channel intensity (blood volume changes modulate light absorption).

  2. Face mode (rPPG): When a face is visible, extracts remote PPG from the
     green channel of the forehead/cheek ROI using the POS algorithm.

The cardiac rhythm (1-2 Hz) maps to the engine's CORE and FAST phi-bands,
providing REAL heart-rate-derived coherence data.

Usage:
  python ppg_sensor.py [--port 7777] [--token TOKEN] [--camera INDEX]

Requires: opencv-python-headless, scipy, numpy
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
    import cv2
except ImportError:
    print('ERROR: opencv-python-headless not installed. Run: pip install opencv-python-headless',
          file=sys.stderr)
    sys.exit(1)

from scipy.signal import butter, sosfilt, find_peaks

logging.basicConfig(
    level=logging.INFO,
    format='[ppg-sensor] %(levelname)s %(message)s',
    stream=sys.stderr,
)
log = logging.getLogger('ppg-sensor')

# --- Constants ---
CAMERA_FPS = 30                 # Target capture FPS
OUTPUT_SAMPLE_RATE = 10.0       # Push to engine at 10 Hz
PUSH_INTERVAL_S = 1.0           # Push every 1 second
SIGNAL_WINDOW_S = 10.0          # Rolling window for PPG signal

# PPG bandpass range (pulse rate)
PULSE_LOW = 0.5                 # Hz (~30 BPM)
PULSE_HIGH = 4.0                # Hz (~240 BPM)

# Finger detection thresholds
FINGER_RED_MEAN_MIN = 100       # Mean red channel when finger covers lens
FINGER_RED_VARIANCE_MAX = 40    # Low variance = uniform coverage


class PPGSensor:
    """Camera-based PPG extraction with auto finger/face detection."""

    def __init__(self, relay_port: int = 7777, relay_token: str = '',
                 camera: int = 0):
        self.relay_url = f'http://localhost:{relay_port}/samples'
        self.relay_token = relay_token
        self.camera_idx = camera
        self._running = False
        self._lock = threading.Lock()

        # Mode tracking
        self._mode = 'detecting'  # 'detecting', 'finger', 'face'
        self._mode_frames = 0

        # Signal buffers (at capture FPS)
        buf_size = int(SIGNAL_WINDOW_S * CAMERA_FPS)
        self._raw_signal = deque(maxlen=buf_size)
        self._timestamps = deque(maxlen=buf_size)

        # Pulse bandpass filter (at camera FPS)
        self._sos_pulse = butter(
            3, [PULSE_LOW, PULSE_HIGH],
            'bandpass', fs=CAMERA_FPS, output='sos'
        )

        # Face detector (Haar cascade, ships with OpenCV)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self._face_cascade = cv2.CascadeClassifier(cascade_path)
        self._face_roi = None
        self._face_detect_interval = 30  # Re-detect face every N frames
        self._frame_count = 0

        # Stats
        self._push_count = 0
        self._last_hr = 0.0

    def _detect_mode(self, frame):
        """Detect whether finger is on camera or face is visible."""
        # Check for finger: high red mean, low variance (uniform red)
        red = frame[:, :, 2]  # BGR → red channel
        red_mean = np.mean(red)
        red_var = np.var(red)

        if red_mean > FINGER_RED_MEAN_MIN and red_var < FINGER_RED_VARIANCE_MAX:
            return 'finger'

        # Check for face
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self._face_cascade.detectMultiScale(
            gray, scaleFactor=1.3, minNeighbors=5, minSize=(80, 80)
        )
        if len(faces) > 0:
            # Use largest face
            areas = [w * h for (x, y, w, h) in faces]
            best = faces[np.argmax(areas)]
            x, y, w, h = best
            # ROI: forehead region (upper 30% of face)
            forehead_y = y
            forehead_h = int(h * 0.3)
            forehead_x = x + int(w * 0.2)
            forehead_w = int(w * 0.6)
            self._face_roi = (forehead_x, forehead_y, forehead_w, forehead_h)
            return 'face'

        return 'detecting'

    def _extract_finger_ppg(self, frame):
        """Extract PPG signal from finger-on-camera (red channel mean)."""
        red = frame[:, :, 2].astype(np.float64)
        return np.mean(red)

    def _extract_face_ppg(self, frame):
        """Extract rPPG signal from face (green channel of forehead ROI)."""
        if self._face_roi is None:
            return None

        x, y, w, h = self._face_roi
        if w <= 0 or h <= 0:
            return None

        # Clamp ROI to frame bounds
        fh, fw = frame.shape[:2]
        x = max(0, min(x, fw - 1))
        y = max(0, min(y, fh - 1))
        w = min(w, fw - x)
        h = min(h, fh - y)

        if w <= 0 or h <= 0:
            return None

        roi = frame[y:y+h, x:x+w]
        green = roi[:, :, 1].astype(np.float64)  # BGR → green channel
        return np.mean(green)

    def _process_and_push(self):
        """Process PPG buffer and push cardiac signal to relay."""
        with self._lock:
            if len(self._raw_signal) < int(CAMERA_FPS * 3):
                return  # Need at least 3 seconds
            raw = np.array(self._raw_signal)

        # Detrend (remove slow drift)
        raw = raw - np.mean(raw)

        # Bandpass filter to pulse range (0.5-4 Hz)
        if len(raw) < 15:
            return

        try:
            filtered = sosfilt(self._sos_pulse, raw)
        except ValueError:
            return

        # Normalize to [-1, 1]
        max_val = np.max(np.abs(filtered))
        if max_val > 1e-10:
            filtered = filtered / max_val

        # Resample from CAMERA_FPS to OUTPUT_SAMPLE_RATE
        n_output = int(len(filtered) * OUTPUT_SAMPLE_RATE / CAMERA_FPS)
        if n_output < 2:
            return

        indices = np.linspace(0, len(filtered) - 1, n_output)
        resampled = np.interp(indices, np.arange(len(filtered)), filtered)

        # Take the last 1 second (10 samples)
        n_push = int(OUTPUT_SAMPLE_RATE * PUSH_INTERVAL_S)
        samples = resampled[-n_push:].tolist()

        # Extract heart rate for logging
        try:
            peaks, _ = find_peaks(filtered, distance=int(CAMERA_FPS * 0.4))
            if len(peaks) >= 2:
                avg_period = np.mean(np.diff(peaks)) / CAMERA_FPS
                self._last_hr = 60.0 / avg_period if avg_period > 0 else 0
        except Exception:
            pass

        # Push to relay
        stream_name = f'ppg_{self._mode}' if self._mode != 'detecting' else 'ppg'
        self._push_samples(stream_name, samples, OUTPUT_SAMPLE_RATE)

    def _push_samples(self, stream_name: str, samples: list, sample_rate: float):
        """Push samples to the bloom relay /samples endpoint."""
        payload = json.dumps({
            'stream': stream_name,
            'samples': samples,
            'sample_rate': sample_rate,
            'source': 'camera',
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
                        f'Push #{self._push_count} [{self._mode}]: '
                        f'HR={self._last_hr:.0f}BPM '
                        f'coherence={coherence:.3f}'
                    )
        except URLError as e:
            if self._push_count == 0:
                log.error(f'Cannot reach relay at {self.relay_url}: {e}')
        except Exception as e:
            log.debug(f'Push error: {e}')

    def start(self):
        """Start camera capture and PPG extraction."""
        self._running = True

        # Open camera
        cap = cv2.VideoCapture(self.camera_idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            # Try without DirectShow
            cap = cv2.VideoCapture(self.camera_idx)
        if not cap.isOpened():
            log.error(f'Cannot open camera {self.camera_idx}')
            return

        # Set resolution (lower = faster)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)

        actual_fps = cap.get(cv2.CAP_PROP_FPS)
        log.info(f'Camera {self.camera_idx} opened at {actual_fps:.0f}fps')

        # Timing
        frame_interval = 1.0 / CAMERA_FPS
        last_push_time = time.time()
        last_mode_check = 0

        log.info(f'PPG sensor active. Pushing to {self.relay_url} every {PUSH_INTERVAL_S}s')

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    log.warning('Frame capture failed, retrying...')
                    time.sleep(0.1)
                    continue

                self._frame_count += 1
                now = time.time()

                # Detect mode periodically
                if self._frame_count % self._face_detect_interval == 0:
                    new_mode = self._detect_mode(frame)
                    if new_mode != self._mode:
                        if new_mode != 'detecting':
                            log.info(f'Mode changed: {self._mode} -> {new_mode}')
                        self._mode = new_mode
                        self._mode_frames = 0
                        # Clear buffer on mode change (signal characteristics differ)
                        with self._lock:
                            self._raw_signal.clear()
                            self._timestamps.clear()

                # Extract PPG value based on mode
                value = None
                if self._mode == 'finger':
                    value = self._extract_finger_ppg(frame)
                elif self._mode == 'face':
                    value = self._extract_face_ppg(frame)

                if value is not None:
                    with self._lock:
                        self._raw_signal.append(value)
                        self._timestamps.append(now)
                    self._mode_frames += 1

                # Push at interval
                if now - last_push_time >= PUSH_INTERVAL_S:
                    if self._mode != 'detecting':
                        self._process_and_push()
                    last_push_time = now

                # Throttle to target FPS
                elapsed = time.time() - now
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            pass
        finally:
            cap.release()
            self.stop()

    def stop(self):
        """Stop camera capture."""
        self._running = False
        log.info(f'PPG sensor stopped. Total pushes: {self._push_count}')


def main():
    parser = argparse.ArgumentParser(description='Camera-based PPG sensor')
    parser.add_argument('--port', type=int, default=7777, help='Bloom relay port')
    parser.add_argument('--token', type=str, default='', help='Relay auth token')
    parser.add_argument('--camera', type=int, default=0, help='Camera device index')
    parser.add_argument('--list-cameras', action='store_true', help='Probe cameras and exit')
    args = parser.parse_args()

    if args.list_cameras:
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                fps = cap.get(cv2.CAP_PROP_FPS)
                print(f'Camera {i}: {w:.0f}x{h:.0f} @ {fps:.0f}fps')
                cap.release()
            else:
                break
        return

    token = args.token or os.environ.get('BLOOM_RELAY_TOKEN', '')

    sensor = PPGSensor(
        relay_port=args.port,
        relay_token=token,
        camera=args.camera,
    )

    def handle_signal(sig, frame):
        sensor.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    sensor.start()


if __name__ == '__main__':
    main()
