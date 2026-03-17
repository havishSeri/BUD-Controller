#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver();

#define SERVO_MIN 150
#define SERVO_MAX 600
#define CENTER 375

int servoPos[5] = {CENTER, CENTER, CENTER, CENTER, CENTER};

void setup() {
  Serial.begin(115200);
  pwm.begin();
  pwm.setPWMFreq(60);
  for (int i = 0; i < 5; i++) pwm.setPWM(i, 0, servoPos[i]);
}

void loop() {
  while (Serial.available() > 0) {
    char cmd = Serial.read();

    if (cmd == 'a') servoPos[0] -= 20;
    if (cmd == 'd') servoPos[0] += 20;
    if (cmd == 'w') servoPos[1] += 3;
    if (cmd == 's') servoPos[1] -= 3;
    if (cmd == 'q') servoPos[2] -= 15;
    if (cmd == 'e') servoPos[2] += 15;
    if (cmd == 'j') servoPos[3] -= 25;
    if (cmd == 'l') servoPos[3] += 25;
    
    // 5th Servo commands
    if (cmd == 'u') servoPos[4] += 15;
    if (cmd == 'i') servoPos[4] -= 15;

    if (cmd == 'c') {
      for (int i = 0; i < 5; i++) servoPos[i] = CENTER;
    }

    for (int i = 0; i < 5; i++) {
      servoPos[i] = constrain(servoPos[i], SERVO_MIN, SERVO_MAX);
      pwm.setPWM(i, 0, servoPos[i]);
    }
  }
}
