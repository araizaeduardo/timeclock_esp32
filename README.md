# Sistema de Control de Asistencia

Sistema moderno de control de asistencia con firmas digitales y notificaciones SMS.

## Características Principales

### 1. Registro de Asistencia
- ✅ Check-in y Check-out con firma digital
- ✅ Validación de registros duplicados
- ✅ Interfaz moderna y responsiva
- ✅ Firma digital con pad táctil
- ✅ Validación de secuencia entrada/salida

### 2. Sistema de Notificaciones
- ✅ Alertas SMS automáticas vía Telnyx
- ✅ Recordatorios después de 8 horas sin check-out
- ✅ Prevención de spam (máximo 1 SMS cada 2 horas)
- ✅ Formato internacional de números automático
- ✅ Registro de notificaciones enviadas

### 3. Panel de Administración
- ✅ Gestión de empleados (alta/baja)
- ✅ Control de estado activo/inactivo
- ✅ Registro de teléfonos para notificaciones
- ✅ Vista de registros de asistencia
- ✅ Reportes en Excel

### 4. Seguridad
- ✅ Autenticación de usuarios
- ✅ Protección CSRF
- ✅ Roles (admin/empleado)
- ✅ Validación de datos
- ✅ Logging de eventos

## Instrucciones

### Instalación

1. Clona el repositorio con el comando `git clone https://github.com/tu-usuario/tu-repositorio`
2. Instala las dependencias con `pip install -r requirements.txt`
3. Configura las variables de entorno en un archivo `.env` con los siguientes valores:
   - `FLASK_SECRET_KEY=your-secret-key`
   - `TELYNX_API_KEY=your-api-key`
   - `TELYNX_PHONE_NUMBER=your-phone-number`
4. Inicia el servidor con `python app.py`

### Uso

1. Abre un navegador y accede a `http://localhost:5000`
2. Inicia sesión con el usuario y contraseña predeterminados (admin/admin123)
3. Haz clic en "Panel de Administración" y agrega un empleado
4. Haz clic en "Registro de Asistencia" y haz un check-in con la tarjeta NFC
5. Haz clic en "Notificaciones" y envía un SMS de prueba

## Contribuir

1. Haz un fork del repositorio
2. Crea una rama para tu feature
3. Haz commit de tus cambios
4. Push a la rama
5. Crea un Pull Request

## Licencia

Este proyecto está bajo la Licencia MIT.
