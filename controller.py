#!/usr/bin/env python3
"""
Xbox Controller to Arduino Servo Bridge
- 100Hz update loop via background gamepad thread
- Fast but controllable speeds
"""

import serial
import time
import threading
from inputs import get_gamepad

# ========== CONFIGURATION ==========
ARDUINO_PORT = 'COM3'
BAUD_RATE = 115200

AXIS_MAP = {
    'ABS_X':  0,
    'ABS_Y':  1,
    'ABS_RX': 2
}

# Degrees per second — higher = faster
SPEED = {
    0: 180,  # Base:     full 180° in 1 sec
    1: 120,  # Shoulder: fast but slightly restrained
    2: 160,  # Elbow
}

INVERT = {
    0: False,
    1: False,
    2: False
}

DEADZONE = {
    'ABS_X':  2000,   # Tighter deadzone = more responsive
    'ABS_Y':  2000,
    'ABS_RX': 2000
}

UPDATE_HZ = 100
UPDATE_INTERVAL = 1.0 / UPDATE_HZ

# Minimum angle change before sending command (lower = smoother but more serial traffic)
MIN_DELTA = 0.3
# ===================================

servo_positions = {0: 90.0, 1: 90.0, 2: 90.0}
axis_values = {axis: 0 for axis in AXIS_MAP}
axis_lock = threading.Lock()
button_events = []
button_lock = threading.Lock()
stop_flag = threading.Event()


def gamepad_thread():
    while not stop_flag.is_set():
        try:
            events = get_gamepad()
            for event in events:
                if event.ev_type == 'Absolute' and event.code in AXIS_MAP:
                    with axis_lock:
                        axis_values[event.code] = event.state
                elif event.ev_type == 'Key' and event.state == 1:
                    with button_lock:
                        button_events.append(event.code)
        except Exception:
            time.sleep(0.005)


def get_rate(axis, value):
    dead = DEADZONE.get(axis, 2000)
    if abs(value) < dead:
        return 0.0
    sign = 1 if value > 0 else -1
    # Smooth curve: ease in from deadzone edge
    norm = (abs(value) - dead) / (32767.0 - dead)
    norm = sign * min(norm, 1.0) ** 0.8   # <-- power < 1 = more responsive at low deflection
    servo_id = AXIS_MAP[axis]
    if INVERT.get(servo_id, False):
        norm = -norm
    return norm


def main():
    ser = None
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Connected to Arduino on {ARDUINO_PORT}")
        print(f"Running at {UPDATE_HZ}Hz | Speeds: {SPEED} | Ctrl+C to exit\n")

        t = threading.Thread(target=gamepad_thread, daemon=True)
        t.start()

        last_time = time.perf_counter()

        while True:
            now = time.perf_counter()
            sleep_time = UPDATE_INTERVAL - (now - last_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

            now = time.perf_counter()
            dt = min(now - last_time, 0.05)  # cap dt to avoid jumps after lag spikes
            last_time = now

            # --- Buttons ---
            with button_lock:
                pending = button_events[:]
                button_events.clear()

            for code in pending:
                if code == 'BTN_SOUTH':
                    ser.write(b"CLAW_CLOSE\n")
                    print("Claw CLOSE")
                elif code == 'BTN_EAST':
                    ser.write(b"CLAW_OPEN\n")
                    print("Claw OPEN")
                elif code == 'BTN_START':
                    for sid in servo_positions:
                        servo_positions[sid] = 90.0
                    ser.write(b"HOME\n")
                    print("All servos HOME")

            # --- Servos ---
            with axis_lock:
                current_axes = axis_values.copy()

            for axis, servo_id in AXIS_MAP.items():
                rate = get_rate(axis, current_axes[axis])
                if rate == 0.0:
                    continue

                delta = rate * SPEED[servo_id] * dt
                new_pos = max(0.0, min(180.0, servo_positions[servo_id] + delta))

                if abs(new_pos - servo_positions[servo_id]) >= MIN_DELTA:
                    servo_positions[servo_id] = new_pos
                    ser.write(f"S{servo_id} {int(round(new_pos))}\n".encode())

    except serial.SerialException as e:
        print(f"ERROR: Cannot open {ARDUINO_PORT} — {e}")
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        stop_flag.set()
        if ser and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()
