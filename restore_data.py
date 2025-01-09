import sqlite3
import os
from datetime import datetime

def restore_database():
    print("Iniciando restauración de la base de datos...")
    
    # Verificar si existe el backup
    if not os.path.exists('timeclock.db.backup'):
        print("Error: No se encontró el archivo de backup")
        return
    
    # Conectar a la base de datos antigua (backup)
    old_conn = sqlite3.connect('timeclock.db.backup')
    old_cursor = old_conn.cursor()
    
    # Conectar a la nueva base de datos
    if os.path.exists('timeclock.db'):
        os.rename('timeclock.db', 'timeclock.db.temp')
        print("Base de datos actual respaldada como timeclock.db.temp")
    
    new_conn = sqlite3.connect('timeclock.db')
    new_cursor = new_conn.cursor()
    
    try:
        # Crear las nuevas tablas
        print("Creando estructura de la nueva base de datos...")
        new_cursor.executescript('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                nfc_id TEXT UNIQUE,
                department TEXT,
                position TEXT,
                schedule_in TEXT,
                schedule_out TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                check_in TIMESTAMP,
                check_out TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Migrar empleados
        print("Migrando empleados...")
        old_cursor.execute('SELECT id, name, nfc_id, is_active, phone_number FROM employees')
        employees = old_cursor.fetchall()
        
        for emp in employees:
            print(f"Migrando empleado: {emp[1]}")
            new_cursor.execute('''
                INSERT INTO employees 
                (id, name, email, phone, nfc_id, department, position, 
                 schedule_in, schedule_out, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                emp[0],          # id
                emp[1],          # name
                None,            # email
                emp[4],          # phone
                emp[2],          # nfc_id
                'General',       # department
                'Empleado',      # position
                '09:00',         # schedule_in
                '18:00',         # schedule_out
                emp[3]           # is_active
            ))
        
        print(f"Migrados {len(employees)} empleados")
        
        # Migrar registros de asistencia
        print("\nMigrando registros de asistencia...")
        old_cursor.execute('''
            SELECT employee_id, timestamp, action 
            FROM time_logs 
            ORDER BY employee_id, timestamp
        ''')
        time_logs = old_cursor.fetchall()
        
        current_employee = None
        check_in_time = None
        attendance_count = 0
        
        for log in time_logs:
            employee_id, timestamp, action = log
            
            if action.lower() == 'entrada':
                if current_employee == employee_id and check_in_time:
                    # Si hay una entrada sin salida, cerrar el registro anterior
                    new_cursor.execute('''
                        INSERT INTO attendance (employee_id, check_in, check_out)
                        VALUES (?, ?, ?)
                    ''', (current_employee, check_in_time, None))
                    attendance_count += 1
                
                current_employee = employee_id
                check_in_time = timestamp
            
            elif action.lower() == 'salida' and current_employee == employee_id:
                if check_in_time:
                    new_cursor.execute('''
                        INSERT INTO attendance (employee_id, check_in, check_out)
                        VALUES (?, ?, ?)
                    ''', (current_employee, check_in_time, timestamp))
                    attendance_count += 1
                    check_in_time = None
        
        # Insertar último registro si quedó pendiente
        if check_in_time:
            new_cursor.execute('''
                INSERT INTO attendance (employee_id, check_in, check_out)
                VALUES (?, ?, ?)
            ''', (current_employee, check_in_time, None))
            attendance_count += 1
        
        new_conn.commit()
        print(f"Migrados {attendance_count} registros de asistencia")
        print("\nMigración completada exitosamente!")
        
        if os.path.exists('timeclock.db.temp'):
            os.remove('timeclock.db.temp')
            print("Archivo temporal eliminado")
        
    except Exception as e:
        print(f"\nError durante la migración: {str(e)}")
        new_conn.rollback()
        
        # Restaurar base de datos original si algo salió mal
        if os.path.exists('timeclock.db.temp'):
            if os.path.exists('timeclock.db'):
                os.remove('timeclock.db')
            os.rename('timeclock.db.temp', 'timeclock.db')
            print("Se ha restaurado la base de datos original")
    
    finally:
        old_conn.close()
        new_conn.close()

def initialize_database():
    print("Iniciando creación de la base de datos...")
    
    # Conectar a la nueva base de datos
    new_conn = sqlite3.connect('timeclock.db')
    new_cursor = new_conn.cursor()
    
    try:
        # Crear las nuevas tablas
        print("Creando estructura de la base de datos...")
        new_cursor.executescript('''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                nfc_id TEXT UNIQUE,
                department TEXT,
                position TEXT,
                schedule_in TEXT,
                schedule_out TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                check_in TIMESTAMP,
                check_out TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            );

            CREATE TABLE IF NOT EXISTS config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Insertar algunos datos de ejemplo
        print("\nCreando datos de ejemplo...")
        
        # Insertar empleados de ejemplo
        employees = [
            (1, 'Juan Pérez', 'juan@example.com', '555-0001', '04A5B9C2', 'Ventas', 'Vendedor', '09:00', '18:00', 1),
            (2, 'María García', 'maria@example.com', '555-0002', '14B5C9D2', 'Administración', 'Asistente', '08:00', '17:00', 1),
            (3, 'Carlos López', 'carlos@example.com', '555-0003', '24C5D9E2', 'IT', 'Programador', '10:00', '19:00', 1),
        ]
        
        for emp in employees:
            print(f"Agregando empleado: {emp[1]}")
            new_cursor.execute('''
                INSERT INTO employees 
                (id, name, email, phone, nfc_id, department, position, 
                 schedule_in, schedule_out, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', emp)
        
        print(f"\nAgregados {len(employees)} empleados de ejemplo")
        
        new_conn.commit()
        print("\nBase de datos inicializada exitosamente!")
        
    except Exception as e:
        print(f"\nError durante la inicialización: {str(e)}")
        new_conn.rollback()
        if os.path.exists('timeclock.db'):
            os.remove('timeclock.db')
            print("Se ha eliminado la base de datos incompleta")
    
    finally:
        new_conn.close()

if __name__ == '__main__':
    restore_database()
    initialize_database()
