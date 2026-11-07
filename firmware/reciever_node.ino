// VELOR RECEIVER NODE
// ESP8266 + HC-12 + Wi-Fi + FastAPI

#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <SoftwareSerial.h>


// Enter your actual credentials locally.
// Do not publish your real Wi-Fi password.

const char* WIFI_SSID =
    "YOUR_WIFI_NAME";

const char* WIFI_PASS =
    "YOUR_WIFI_PASSWORD";

const char* SERVER_URL =
    "http://YOUR_LAPTOP_IP:8000/api/gauge";


// HC-12 connections
const int HC12_RX_PIN = D2;
const int HC12_TX_PIN = D1;

const int ledPin = D7;


// SoftwareSerial format: RX, TX
SoftwareSerial hc12(
    HC12_RX_PIN,
    HC12_TX_PIN
);


String line = "";

bool dashboardOk = false;
bool linkWasUp = false;

unsigned long lastPacket = 0;
unsigned long lastWifiTry = 0;


// Wi-Fi connection
void connectWiFi() {

  Serial.print("Connecting to Wi-Fi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);

  WiFi.begin(WIFI_SSID, WIFI_PASS);

  unsigned long start = millis();

  while (
      WiFi.status() != WL_CONNECTED &&
      millis() - start < 15000
  ) {

    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {

    Serial.println(
        "ESP8266 CONNECTED to Wi-Fi"
    );

    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());

  } else {

    Serial.println(
        "Wi-Fi NOT connected - will keep retrying"
    );
  }
}


// Send data to FastAPI
void postToDashboard(
    const String& distance,
    const String& height,
    const String& status
) {

  if (WiFi.status() != WL_CONNECTED)
    return;

  WiFiClient client;

  HTTPClient http;

  if (!http.begin(client, SERVER_URL))
    return;

  http.setTimeout(5000);

  http.addHeader(
      "Content-Type",
      "application/json"
  );


  // The backend calculates water_level_cm
  // from distance_cm and sensor_height_cm.

  String body =
      "{\"distance_cm\":" + distance +
      ",\"sensor_height_cm\":" + height +
      ",\"source\":\"VELOR HC-12\"}";


  int code = http.POST(body);


  if (code >= 200 && code < 300) {

    if (!dashboardOk) {

      Serial.println(
          "ESP8266 CONNECTED to DASHBOARD"
      );

      dashboardOk = true;
    }

    Serial.println(
        "Forwarded to dashboard OK"
    );

  } else {

    dashboardOk = false;

    Serial.print("Dashboard error HTTP ");
    Serial.println(code);

    if (code > 0) {

      Serial.print("Server response: ");
      Serial.println(http.getString());

    } else {

      Serial.println(
          http.errorToString(code)
      );
    }
  }

  http.end();
}


// Process incoming HC-12 packets
// Format:
// G1,distance,waterLevel,status,sensorHeight

void handlePacket(String p) {

  p.trim();

  if (!p.startsWith("G1,"))
    return;


  int c1 = p.indexOf(',');
  int c2 = p.indexOf(',', c1 + 1);
  int c3 = p.indexOf(',', c2 + 1);
  int c4 = p.indexOf(',', c3 + 1);


  if (
      c1 < 0 ||
      c2 < 0 ||
      c3 < 0 ||
      c4 < 0
  )
    return;


  String dist =
      p.substring(c1 + 1, c2);

  String waterLevel =
      p.substring(c2 + 1, c3);

  String status =
      p.substring(c3 + 1, c4);

  String height =
      p.substring(c4 + 1);


  lastPacket = millis();

  if (!linkWasUp) {

    Serial.println(
        "HC-12 LINK UP - receiving from gauge"
    );

    linkWasUp = true;
  }


  digitalWrite(ledPin, HIGH);

  Serial.print("Received: ");
  Serial.println(p);


  if (dist != "ERR") {

    float distanceValue = dist.toFloat();
    float heightValue = height.toFloat();

    if (
        distanceValue < 0 ||
        distanceValue > 1000 ||
        heightValue <= 0 ||
        heightValue > 1000
    ) {

      Serial.println(
          "Invalid sensor values - packet rejected"
      );

    } else {

      postToDashboard(
          dist,
          height,
          status
      );
    }

  } else {

    Serial.println(
        "Invalid ultrasonic reading - not forwarded"
    );
  }


  digitalWrite(ledPin, LOW);
}


void setup() {

  Serial.begin(115200);

  hc12.begin(9600);

  pinMode(ledPin, OUTPUT);

  digitalWrite(ledPin, LOW);

  Serial.println();

  Serial.println(
      "VELOR receiver node (HC-12 + Wi-Fi) started"
  );

  connectWiFi();
}


void loop() {

  // Retry Wi-Fi
  if (
      WiFi.status() != WL_CONNECTED &&
      millis() - lastWifiTry >= 10000
  ) {

    lastWifiTry = millis();

    Serial.println("Retrying Wi-Fi...");

    WiFi.disconnect();

    WiFi.begin(WIFI_SSID, WIFI_PASS);
  }


  // Read incoming radio packets
  while (hc12.available()) {

    char ch = hc12.read();

    if (ch == '\n') {

      handlePacket(line);

      line = "";

    } else if (ch != '\r') {

      line += ch;

      if (line.length() > 100)
        line = "";
    }
  }


  // Check radio link
  if (
      linkWasUp &&
      millis() - lastPacket > 10000
  ) {

    Serial.println(
        "HC-12 LINK LOST - no packets from gauge"
    );

    linkWasUp = false;
  }
}
