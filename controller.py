import serial
import time
import pygame
import threading
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# --- CONFIGURATION ---
PORT = 'COM7'  # Ensure this matches your Arduino port
BAUD = 115200
CENTER = 375

# Shared state between the controller thread and the visualizer
servo_pos = [CENTER, CENTER, CENTER, CENTER]
running = True

# Initialize Serial Connection
try:
    ser = serial.Serial(PORT, BAUD, timeout=0)
    ser.set_buffer_size(rx_size=12800, tx_size=12800)
    print(f"Connected to Arduino on {PORT}")
except Exception as e:
    print(f"Serial Error: {e}")
    exit()

# Initialize DualSense Controller
pygame.init()
pygame.joystick.init()
if pygame.joystick.get_count() == 0:
    print("DualSense not found! Connect via USB or Bluetooth.")
    exit()

ds = pygame.joystick.Joystick(0)
ds.init()
print(f"Controller: {ds.get_name()} ready.")


def controller_logic():
    """Background thread for high-speed controller input and Serial output."""
    global servo_pos, running

    while running:
        pygame.event.pump()

        # DualSense Axis Mapping
        lx = ds.get_axis(0)  # Left Stick X -> Base (S0)
        ly = ds.get_axis(1)  # Left Stick Y -> Shoulder (S1)
        rx = ds.get_axis(2)  # Right Stick X -> Elbow (S2)
        r2 = ds.get_axis(4)  # R2 Trigger -> Gripper (S3)

        # SERVO 0: Base (A/D) - Speed 20
        if lx < -0.3:
            ser.write(b'a')
            servo_pos[0] -= 20
        elif lx > 0.3:
            ser.write(b'd')
            servo_pos[0] += 20

        # SERVO 1: Shoulder (W/S) - Speed 3 (Fixed for precision)
        if ly < -0.3:
            ser.write(b'w')
            servo_pos[1] += 3
        elif ly > 0.3:
            ser.write(b's')
            servo_pos[1] -= 3

        # SERVO 2: Elbow (Q/E) - Speed 15
        if rx < -0.3:
            ser.write(b'q')
            servo_pos[2] -= 15
        elif rx > 0.3:
            ser.write(b'e')
            servo_pos[2] += 15

        # SERVO 3: Gripper (J/L) - Speed 25
        # DIRECTION SWAPPED: Squeezing R2 now sends 'j' (Close/Down)
        if r2 > -0.5:
            ser.write(b'j')
            servo_pos[3] -= 25
        else:
            ser.write(b'l')
            servo_pos[3] += 25

        # Center All (PS Button - index 10)
        if ds.get_button(10):
            ser.write(b'c')
            servo_pos = [CENTER, CENTER, CENTER, CENTER]

        # Clamp values for the visualizer
        for i in range(4):
            servo_pos[i] = max(150, min(600, servo_pos[i]))

        time.sleep(0.01)  # 100Hz polling rate


# Start the Controller Thread
comm_thread = threading.Thread(target=controller_logic, daemon=True)
comm_thread.start()

# --- MAIN THREAD: 3D Visualizer ---
plt.ion()
fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

try:
    while True:
        s = servo_pos[:]  # Snapshot current positions

        ax.clear()
        ax.set_xlim([-15, 15]);
        ax.set_ylim([-15, 15]);
        ax.set_zlim([0, 20])
        ax.set_title(f"Live Arm Data | S3 Direction: Swapped")

        # Pulse to Radians conversion
        r0 = np.radians((s[0] - 375) / 2.5)
        r1 = np.radians((s[1] - 375) / 2.5)
        r2_angle = np.radians((s[2] - 375) / 2.5)

        # 3D Line Model Math
        x0, y0, z0 = 0, 0, 0
        x1, y1, z1 = 0, 0, 4  # Base

        # Shoulder link
        x2 = x1 + 7 * np.cos(r1) * np.cos(r0)
        y2 = y1 + 7 * np.cos(r1) * np.sin(r0)
        z2 = z1 + 7 * np.sin(r1)

        # Elbow link
        x3 = x2 + 5 * np.cos(r1 + r2_angle) * np.cos(r0)
        y3 = y2 + 5 * np.cos(r1 + r2_angle) * np.sin(r0)
        z3 = z2 + 5 * np.sin(r1 + r2_angle)

        # Plotting
        ax.plot([x0, x1, x2, x3], [y0, y1, y2, y3], [z0, z1, z2, z3], 'bo-', lw=5, markersize=8)

        plt.draw()
        plt.pause(0.03)

except KeyboardInterrupt:
    print("\nStopping...")
    running = False
    ser.close()
    pygame.quit()