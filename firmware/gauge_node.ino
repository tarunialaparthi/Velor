// VELOR GAUGE NODE
// ESP32 + HC-SR04 + LED + HC-12 transmitter

const int HC12_RX = 32;
const int HC12_TX = 33;

const int trigPin = 25;
const int echoPin = 26;
const int ledPin = 27;

const float SENSOR_HEIGHT_CM = 20.0;
const float BLINK_CM = 5.0;
const float ON_CM = 10.0;
const float HYST_CM = 0.5;
const float AIR_TEMP_C = 28.0;
const float HEIGHT_TOLERANCE_CM = 1.0;

const unsigned long MEASURE_INTERVAL_MS = 500;
const unsigned long SEND_INTERVAL_MS = 1000;

enum Level { SAFE, WARNING, DANGER, NO_ECHO };

Level currentLevel = SAFE;

unsigned long lastMeasure = 0;
unsigned long lastSend = 0;
unsigned long lastBlink = 0;

bool ledState = false;


// Ultrasonic measurement
float readDistanceCm() {

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);

  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);

  digitalWrite(trigPin, LOW);

  unsigned long duration =
      pulseIn(echoPin, HIGH, 30000UL);

  if (duration == 0) return -1.0;

  float speedCmPerUs =
      (331.4 + 0.606 * AIR_TEMP_C) / 10000.0;

  return duration * speedCmPerUs / 2.0;
}


// Median filter
float getStableDistance() {

  float r[5];
  int count = 0;

  for (int i = 0; i < 5; i++) {

    float d = readDistanceCm();

    if (d > 0) {
      r[count++] = d;
    }

    delay(50);
  }

  if (count == 0) return -1.0;

  for (int i = 0; i < count - 1; i++) {

    for (int j = i + 1; j < count; j++) {

      if (r[j] < r[i]) {

        float t = r[i];
        r[i] = r[j];
        r[j] = t;

      }
    }
  }

  return r[count / 2];
}


// Water-level status
Level getLevel(float w, Level prev) {

  Level up;

  if (w >= ON_CM)
    up = DANGER;

  else if (w >= BLINK_CM)
    up = WARNING;

  else
    up = SAFE;

  if (prev == NO_ECHO || up >= prev)
    return up;

  Level down;

  if (w >= ON_CM - HYST_CM)
    down = DANGER;

  else if (w >= BLINK_CM - HYST_CM)
    down = WARNING;

  else
    down = SAFE;

  return (down > up) ? down : up;
}


const char* levelName(Level l) {

  switch (l) {

    case SAFE:
      return "SAFE";

    case WARNING:
      return "WARNING";

    case DANGER:
      return "DANGER";

    default:
      return "NO_ECHO";
  }
}


// HC-12 transmission
void sendPacket(const String& pkt) {

  Serial2.println(pkt);

  Serial.print("Sent via HC-12: ");
  Serial.println(pkt);
}


void setup() {

  Serial.begin(115200);

  Serial2.begin(
      9600,
      SERIAL_8N1,
      HC12_RX,
      HC12_TX
  );

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(ledPin, OUTPUT);

  digitalWrite(trigPin, LOW);
  digitalWrite(ledPin, LOW);

  for (int i = 0; i < 3; i++) {

    digitalWrite(ledPin, HIGH);
    delay(150);

    digitalWrite(ledPin, LOW);
    delay(150);
  }

  Serial.println(
      "VELOR gauge node (HC-12 transmitter) started"
  );
}


void loop() {

  unsigned long now = millis();

  if (now - lastMeasure >= MEASURE_INTERVAL_MS) {

    lastMeasure = now;

    float distance = getStableDistance();

    bool sendNow =
        (now - lastSend >= SEND_INTERVAL_MS);


    if (
        distance < 2.0 ||
        distance > 400.0 ||
        distance > SENSOR_HEIGHT_CM + HEIGHT_TOLERANCE_CM
    ) {

      currentLevel = NO_ECHO;

      Serial.println(
          "NO ECHO / INVALID distance"
      );

      if (sendNow) {

        lastSend = now;

        sendPacket(
            "G1,ERR,ERR,NO_ECHO," +
            String(SENSOR_HEIGHT_CM, 1)
        );
      }

    } else {

      float d = distance;

      if (d > SENSOR_HEIGHT_CM)
        d = SENSOR_HEIGHT_CM;

      float waterLevel =
          max(0.0f, SENSOR_HEIGHT_CM - d);

      currentLevel =
          getLevel(waterLevel, currentLevel);


      Serial.print("Distance: ");
      Serial.print(distance, 1);

      Serial.print(" cm | Water level: ");
      Serial.print(waterLevel, 1);

      Serial.print(" cm | ");

      Serial.println(levelName(currentLevel));


      if (sendNow) {

        lastSend = now;

        sendPacket(
            "G1," +
            String(d, 1) + "," +
            String(waterLevel, 1) + "," +
            levelName(currentLevel) + "," +
            String(SENSOR_HEIGHT_CM, 1)
        );
      }
    }
  }


  // LED indication
  switch (currentLevel) {

    case SAFE:
    case NO_ECHO:

      digitalWrite(ledPin, LOW);
      ledState = false;
      break;


    case WARNING:

      if (now - lastBlink >= 300) {

        lastBlink = now;

        ledState = !ledState;

        digitalWrite(ledPin, ledState);
      }
      break;


    case DANGER:

      digitalWrite(ledPin, HIGH);
      ledState = true;
      break;
  }
}
