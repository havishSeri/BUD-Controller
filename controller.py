import serial
import time
import pygame
import threading
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

PORT = 'COM7'
BAUD = 115200
CENTER = 375

# track all 5 servos
servo_pos = [CENTER] * 5
running = True

try:
    ser = serial.Serial(PORT, BAUD, timeout=0)
    ser.set_buffer_size(rx_size=12800, tx_size=12800)
    print(f"bot connected on {PORT}")
except Exception as e:
    print(f"serial fail {e}")
    exit()

pygame.init()
pygame.joystick.init()
ds = pygame.joystick.Joystick(0)
ds.init()


def controller_logic():
    global servo_pos, running
    while running:
        pygame.event.pump()

        lx, ly = ds.get_axis(0), ds.get_axis(1)
        rx = ds.get_axis(2)

        # base
        if abs(lx) > 0.3:
            ser.write(b'a' if lx < 0 else b'd')
            servo_pos[0] += (-20 if lx < 0 else 20)

        # shoulder
        if abs(ly) > 0.3:
            ser.write(b'w' if ly < 0 else b's')
            servo_pos[1] += (3 if ly < 0 else -3)

        # elbow
        if abs(rx) > 0.3:
            ser.write(b'q' if rx < 0 else b'e')
            servo_pos[2] += (-15 if rx < 0 else 15)

        # gripper on buttons so no snap back
        if ds.get_button(4):
            ser.write(b'j')
            servo_pos[3] -= 25
        elif ds.get_button(5):
            ser.write(b'l')
            servo_pos[3] += 25

        # 5th servo on triangle/cross
        if ds.get_button(2):
            ser.write(b'u')
            servo_pos[4] += 15
        elif ds.get_button(0):
            ser.write(b'i')
            servo_pos[4] -= 15

        # ps button reset
        if ds.get_button(10):
            ser.write(b'c')
            servo_pos = [CENTER] * 5

        # keep servos in range
        for i in range(5):
            servo_pos[i] = max(150, min(600, servo_pos[i]))

        time.sleep(0.01)


threading.Thread(target=controller_logic, daemon=True).start()

# 3d view
plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

try:
    while True:
        s = servo_pos[:]
        ax.clear()
        ax.set_xlim([-20, 20]);
        ax.set_ylim([-20, 20]);
        ax.set_zlim([0, 25])

        # math for the 5 joints
        r0, r1, r2, r4 = [np.radians((pos - 375) / 2.5) for pos in [s[0], s[1], s[2], s[4]]]

        # build the arm lines
        x, y, z = [0, 0], [0, 0], [0, 4]

        # shoulder
        x.append(x[-1] + 7 * np.cos(r1) * np.cos(r0))
        y.append(y[-1] + 7 * np.cos(r1) * np.sin(r0))
        z.append(z[-1] + 7 * np.sin(r1))

        # elbow
        x.append(x[-1] + 5 * np.cos(r1 + r2) * np.cos(r0))
        y.append(y[-1] + 5 * np.cos(r1 + r2) * np.sin(r0))
        z.append(z[-1] + 5 * np.sin(r1 + r2))

        # wrist
        x.append(x[-1] + 3 * np.cos(r1 + r2 + r4) * np.cos(r0))
        y.append(y[-1] + 3 * np.cos(r1 + r2 + r4) * np.sin(r0))
        z.append(z[-1] + 3 * np.sin(r1 + r2 + r4))

        ax.plot(x, y, z, 'bo-', lw=4)
        plt.pause(0.03)
except KeyboardInterrupt:
    running = False
    ser.close()
