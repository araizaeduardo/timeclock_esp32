#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <MFRC522v2.h>
#include <MFRC522DriverSPI.h>
#include <MFRC522DriverPinSimple.h>
#include "config.h"

// Configuración del servidor
const char* serverUrl = SERVER_URL;

// Configuración MFRC522
MFRC522DriverPinSimple ss_pin(NFC_SS_PIN); // SDA
MFRC522DriverSPI driver{ss_pin};
MFRC522 mfrc522{driver};

// LED y Buzzer
#define LED_PIN     2   // LED integrado
#define BUZZER_PIN  4   // Pin para el buzzer

void setup() {
  Serial.begin(115200);
  Serial.println("\nIniciando sistema...");
  
  // Inicializar LED y Buzzer
  pinMode(LED_PIN, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  
  // Inicializar WiFi
  Serial.print("Conectando a WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  // Parpadear LED mientras se conecta
  int intentos = 0;
  while (WiFi.status() != WL_CONNECTED && intentos < 20) {
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    delay(400);
    Serial.print(".");
    intentos++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n¡WiFi conectado!");
    Serial.print("Dirección IP: ");
    Serial.println(WiFi.localIP());
    Serial.print("Fuerza de señal (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    
    // Indicar conexión exitosa con 3 parpadeos rápidos
    for(int i = 0; i < 3; i++) {
      digitalWrite(LED_PIN, HIGH);
      tone(BUZZER_PIN, 1000, 50);
      delay(100);
      digitalWrite(LED_PIN, LOW);
      delay(100);
    }
  } else {
    Serial.println("\n¡Error de conexión WiFi!");
    // Indicar error con parpadeo largo
    digitalWrite(LED_PIN, HIGH);
    tone(BUZZER_PIN, 400, 1000);
    delay(1000);
    digitalWrite(LED_PIN, LOW);
  }
  
  // Inicializar SPI y MFRC522
  SPI.begin();
  mfrc522.PCD_Init();
  delay(4);
  Serial.println("Lector NFC listo");
  
  // Mostrar información del sistema
  Serial.println("\nEstado del sistema:");
  Serial.println("------------------");
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("Canal WiFi: ");
  Serial.println(WiFi.channel());
  Serial.print("Dirección MAC: ");
  Serial.println(WiFi.macAddress());
  Serial.println("------------------");
}

void successBeep() {
  digitalWrite(LED_PIN, HIGH);
  tone(BUZZER_PIN, 1000, 100);
  delay(200);
  digitalWrite(LED_PIN, LOW);
}

void errorBeep() {
  digitalWrite(LED_PIN, HIGH);
  tone(BUZZER_PIN, 400, 200);
  delay(100);
  tone(BUZZER_PIN, 400, 200);
  digitalWrite(LED_PIN, LOW);
}

String getUID() {
  String uidString = "";
  for (byte i = 0; i < mfrc522.uid.size; i++) {
    if (mfrc522.uid.uidByte[i] < 0x10) {
      uidString += "0";
    }
    uidString += String(mfrc522.uid.uidByte[i], HEX);
  }
  uidString.toUpperCase();
  return uidString;
}

void sendUIDToServer(String uid) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    
    // Crear JSON con el UID
    String jsonData = "{\"nfc_id\":\"" + uid + "\"}";
    
    http.begin(serverUrl);
    http.addHeader("Content-Type", "application/json");
    
    int httpResponseCode = http.POST(jsonData);
    
    if (httpResponseCode > 0) {
      String response = http.getString();
      Serial.println("Respuesta del servidor: " + response);
      successBeep();
    } else {
      Serial.println("Error en la petición HTTP");
      errorBeep();
    }
    
    http.end();
  } else {
    Serial.println("Error de conexión WiFi");
    errorBeep();
  }
}

void checkWiFiConnection() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("Conexión WiFi perdida. Reconectando...");
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    // Esperar reconexión
    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 10) {
      digitalWrite(LED_PIN, HIGH);
      delay(100);
      digitalWrite(LED_PIN, LOW);
      delay(400);
      Serial.print(".");
      intentos++;
    }
    
    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n¡WiFi reconectado!");
      Serial.print("Nueva IP: ");
      Serial.println(WiFi.localIP());
    } else {
      Serial.println("\nError de reconexión");
    }
  }
}

void loop() {
  // Verificar conexión WiFi periódicamente
  static unsigned long lastWiFiCheck = 0;
  if (millis() - lastWiFiCheck > 30000) {  // Cada 30 segundos
    checkWiFiConnection();
    lastWiFiCheck = millis();
  }
  
  // Buscar nuevas tarjetas
  if (!mfrc522.PICC_IsNewCardPresent()) {
    delay(50);
    return;
  }
  
  // Seleccionar una tarjeta
  if (!mfrc522.PICC_ReadCardSerial()) {
    delay(50);
    return;
  }
  
  // Obtener y enviar UID
  String uid = getUID();
  Serial.println("Tarjeta detectada: " + uid);
  sendUIDToServer(uid);
  
  // Esperar a que se retire la tarjeta
  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();
  
  delay(1000); // Evitar lecturas múltiples
}
