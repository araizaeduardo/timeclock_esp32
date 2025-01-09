# ESP32 + NFC (MFRC522) para Control de Asistencia

## Componentes Necesarios

1. **ESP32** (cualquier modelo, recomendado ESP32-WROOM)
2. **Módulo MFRC522** (lector NFC)
3. **Buzzer** (opcional, para feedback sonoro)
4. **LED** (opcional, ya incluido en ESP32)
5. **Cables Dupont** para conexiones

## Conexiones

### MFRC522 a ESP32
```
ESP32     ->  MFRC522
3.3V      ->  3.3V/VCC
GND       ->  GND
GPIO23    ->  MOSI
GPIO19    ->  MISO
GPIO18    ->  SCK
GPIO21    ->  SDA/SS
```

### Buzzer (Opcional)
```
ESP32     ->  Buzzer
GPIO4     ->  PIN positivo (+)
GND       ->  PIN negativo (-)
```

## Instalación del Software

### 1. Configurar Arduino IDE para ESP32
1. Abre Arduino IDE
2. Ve a `File -> Preferences` (`Archivo -> Preferencias`)
3. En "Additional Boards Manager URLs" agrega:
   ```
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
   ```
4. Ve a `Tools -> Board -> Boards Manager`
5. Busca "esp32"
6. Instala "ESP32 by Espressif Systems"

### 2. Instalar Biblioteca MFRC522
1. Ve a `Sketch -> Include Library -> Manage Libraries`
2. Busca "MFRC522"
3. Instala "MFRC522 by GithubCommunity" versión 2.0.0 o superior
4. Reinicia Arduino IDE

### 3. Configurar la Placa
1. Selecciona `Tools -> Board -> ESP32 Arduino -> ESP32 Dev Module`
2. Configura:
   - Upload Speed: 115200
   - CPU Frequency: 240MHz
   - Flash Frequency: 80MHz
   - Flash Mode: QIO
   - Flash Size: 4MB
   - Partition Scheme: Default

## Configuración del Código

1. Abre `esp32_nfc.ino`
2. Modifica las variables de conexión:
   ```cpp
   const char* ssid = "TU_WIFI";
   const char* password = "TU_PASSWORD";
   const char* serverUrl = "http://TU_IP:5007/read_nfc";
   ```

## Verificación del Hardware

### 1. Verificar Conexiones
- Usa un multímetro para comprobar:
  - Voltaje en 3.3V del MFRC522
  - Continuidad en conexiones GND
  - No hay cortocircuitos

### 2. LED Indicadores
- **LED del ESP32 (GPIO2)**:
  - Parpadeo rápido = Conectando WiFi
  - Encendido breve = Lectura exitosa
  - Parpadeo doble = Error

- **LED del MFRC522**:
  - Rojo fijo = Alimentación correcta
  - Verde parpadeante = Actividad

## Solución de Problemas

### 1. Errores de Compilación
- Biblioteca MFRC522 v2.0.0 o superior instalada
- ESP32 board package instalado
- Placa correcta seleccionada

### 2. Errores de Conexión WiFi
- Credenciales WiFi correctas
- ESP32 dentro del alcance del router
- Red 2.4GHz (no 5GHz)

### 3. Errores de Lectura NFC
- Cables correctamente conectados
- Voltaje 3.3V estable
- Tarjeta compatible (MIFARE Classic/M302)
- Distancia de lectura adecuada (0-3cm)

### 4. Errores de Comunicación con Servidor
- URL del servidor correcta
- Servidor ejecutándose
- Puerto 5007 accesible
- ESP32 y servidor en la misma red

## Mantenimiento

### Recomendaciones
1. Mantener el firmware actualizado
2. Limpiar periódicamente los contactos
3. Verificar voltajes mensualmente
4. Mantener registro de errores
5. Backup del código

### Mejoras Futuras
- [ ] Modo de bajo consumo
- [ ] Pantalla OLED
- [ ] Almacenamiento offline
- [ ] Múltiples lectores
- [ ] Encriptación de datos


### PRUEBAS
curl -X POST http://localhost:5000/check -d nfc_id=04A5B9C2

curl -X POST http://localhost:5000/check -d nfc_id=04A5B9C2 -H Content-Type: application/x-www-form-urlencoded