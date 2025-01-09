# Sistema de Control de Asistencia con ESP32 y MFRC522

Este proyecto implementa un lector NFC usando ESP32 y el módulo MFRC522 para registrar asistencia de empleados.

## Requisitos de Hardware

- ESP32 DevKit
- Módulo MFRC522 (Lector NFC)
- LED (incorporado en ESP32)
- Buzzer (opcional)
- Cables de conexión

## Conexiones

1. **MFRC522 a ESP32**:
   - SDA (SS) -> GPIO 5
   - SCK -> GPIO 18
   - MOSI -> GPIO 23
   - MISO -> GPIO 19
   - RST -> GPIO 27
   - VCC -> 3.3V
   - GND -> GND

2. **Buzzer**:
   - Pin positivo -> GPIO 4
   - Pin negativo -> GND

## Configuración del Software

1. **Instalar Dependencias**:
   En el Arduino IDE, instalar las siguientes bibliotecas:
   - MFRC522 (por GithubCommunity)
   - ESP32 (por Espressif Systems)

2. **Configuración del Proyecto**:
   ```bash
   # 1. Clonar el repositorio
   git clone https://github.com/tu-usuario/timeclock.git
   cd timeclock/esp32_nfc

   # 2. Copiar el archivo de configuración
   cp config.example.h config.h
   ```

3. **Editar Configuración**:
   Abrir `config.h` y configurar:
   ```cpp
   // Credenciales WiFi
   #define WIFI_SSID "tu-red-wifi"
   #define WIFI_PASSWORD "tu-contraseña-wifi"

   // Configuración del servidor
   #define SERVER_HOST "ip-de-tu-servidor"
   #define SERVER_PORT 5007

   // Pines (modificar si usas diferentes conexiones)
   #define NFC_SS_PIN 5
   #define NFC_RST_PIN 27
   ```

## Compilación y Carga

1. Abrir Arduino IDE
2. Seleccionar la placa: `Tools -> Board -> ESP32 -> ESP32 Dev Module`
3. Seleccionar el puerto COM correcto
4. Compilar y cargar el código

## Uso

1. Al encender, el ESP32:
   - Intentará conectarse al WiFi (LED parpadeando)
   - LED encendido fijo = conectado
   - LED apagado = error de conexión

2. Para registrar asistencia:
   - Acercar la tarjeta NFC al lector
   - Beep corto = lectura exitosa
   - Beep largo = error de lectura

3. Indicadores:
   - LED parpadeando rápido = procesando tarjeta
   - Beep doble = registro exitoso
   - Beep largo = error en el registro

## Solución de Problemas

1. **No se conecta al WiFi**:
   - Verificar credenciales en `config.h`
   - Asegurar que la red esté disponible
   - Revisar que el ESP32 esté en rango

2. **Error de lectura NFC**:
   - Verificar conexiones del MFRC522
   - Asegurar que la tarjeta sea compatible
   - Mantener la tarjeta más cerca del lector

3. **No se registra la asistencia**:
   - Verificar que el servidor esté funcionando
   - Comprobar la IP y puerto en `config.h`
   - Revisar la conexión de red

## Mantenimiento

- Mantener el lector limpio
- Verificar periódicamente las conexiones
- Actualizar el firmware cuando sea necesario
- Hacer respaldo del archivo `config.h`

## Seguridad

- No compartir el archivo `config.h`
- Cambiar las contraseñas periódicamente
- Mantener el firmware actualizado
- Usar tarjetas NFC seguras

## Contribuir

1. Hacer fork del repositorio
2. Crear una rama para tu feature
3. Hacer commit de tus cambios
4. Crear un pull request

## Licencia

Este proyecto está bajo la Licencia MIT.