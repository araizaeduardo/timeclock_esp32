import sqlite3
import os
import hashlib
from datetime import datetime

def reset_database():
    print("Iniciando reinicialización de la base de datos...")
    
    # Eliminar base de datos existente si existe
    if os.path.exists('timeclock.db'):
        os.remove('timeclock.db')
        print("Base de datos anterior eliminada")
    
    # Conectar a la nueva base de datos
    conn = sqlite3.connect('timeclock.db')
    cursor = conn.cursor()
    
    try:
        # Leer y ejecutar el schema
        with open('schema.sql', 'r') as f:
            cursor.executescript(f.read())
        print("Estructura de la base de datos creada")
        
        # Crear admin por defecto
        username = 'admin'
        password = 'admin123'
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            INSERT INTO admins (username, password, name, email)
            VALUES (?, ?, ?, ?)
        ''', (username, hashed_password, 'Administrador', 'admin@example.com'))
        print("\nAdministrador creado:")
        print(f"Usuario: {username}")
        print(f"Contraseña: {password}")
        
        # Crear algunos empleados de ejemplo
        employees = [
            ('Juan Pérez', 'juan@example.com', '555-0001', '04A5B9C2', 'Ventas', 'Vendedor', '09:00', '18:00', 1),
            ('María García', 'maria@example.com', '555-0002', '14B5C9D2', 'Administración', 'Asistente', '08:00', '17:00', 1),
            ('Carlos López', 'carlos@example.com', '555-0003', '24C5D9E2', 'IT', 'Programador', '10:00', '19:00', 1),
        ]
        
        for emp in employees:
            cursor.execute('''
                INSERT INTO employees 
                (name, email, phone, nfc_id, department, position, 
                 schedule_in, schedule_out, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', emp)
            print(f"Empleado agregado: {emp[0]}")
        
        # Crear algunos registros de asistencia de ejemplo
        today = datetime.now().strftime('%Y-%m-%d')
        attendance = [
            (1, f'{today} 08:55:00', f'{today} 17:05:00'),
            (2, f'{today} 07:58:00', f'{today} 16:02:00'),
            (3, f'{today} 10:05:00', None),  # Todavía no sale
        ]
        
        for att in attendance:
            cursor.execute('''
                INSERT INTO attendance (employee_id, check_in, check_out)
                VALUES (?, ?, ?)
            ''', att)
        print("\nRegistros de asistencia de ejemplo creados")
        
        conn.commit()
        print("\nBase de datos inicializada exitosamente!")
        
    except Exception as e:
        print(f"\nError durante la inicialización: {str(e)}")
        conn.rollback()
        if os.path.exists('timeclock.db'):
            os.remove('timeclock.db')
            print("Se ha eliminado la base de datos incompleta")
    
    finally:
        conn.close()

if __name__ == '__main__':
    reset_database()
