import sqlite3
import os
from datetime import datetime

def create_new_tables(cursor):
    """Crear las nuevas tablas en la base de datos."""
    cursor.executescript('''
        -- Tabla de empleados
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

        -- Tabla de asistencia
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            check_in TIMESTAMP,
            check_out TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        );

        -- Tabla de configuración
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    ''')

def migrate_database():
    # Verificar si existe backup
    if not os.path.exists('timeclock.db.backup'):
        print("No se encontró archivo de backup")
        return
    
    # Conectar a la base de datos antigua
    old_conn = sqlite3.connect('timeclock.db.backup')
    old_cursor = old_conn.cursor()
    
    # Conectar a la nueva base de datos
    new_conn = sqlite3.connect('timeclock.db')
    new_cursor = new_conn.cursor()
    
    try:
        # Crear las nuevas tablas primero
        print("Creando nuevas tablas...")
        create_new_tables(new_cursor)
        new_conn.commit()
        print("Tablas creadas exitosamente")

        # Obtener datos de empleados de la base antigua
        print("Migrando empleados...")
        old_cursor.execute('SELECT id, name, nfc_id, is_active, phone_number FROM employees')
        employees = old_cursor.fetchall()
        
        # Insertar en la nueva base de datos
        for emp in employees:
            new_cursor.execute('''
                INSERT INTO employees 
                (id, name, email, phone, nfc_id, department, position, 
                 schedule_in, schedule_out, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                emp[0],          # id
                emp[1],          # name
                None,            # email (nuevo campo)
                emp[4],          # phone (antes phone_number)
                emp[2],          # nfc_id
                'General',       # department (nuevo campo)
                'Empleado',      # position (nuevo campo)
                '09:00',         # schedule_in (nuevo campo)
                '18:00',         # schedule_out (nuevo campo)
                emp[3]           # is_active
            ))
        print(f"Migrados {len(employees)} empleados")
        
        # Migrar registros de asistencia
        print("Migrando registros de asistencia...")
        old_cursor.execute('''
            SELECT employee_id, timestamp, action 
            FROM time_logs 
            ORDER BY employee_id, timestamp
        ''')
        time_logs = old_cursor.fetchall()
        
        # Procesar los registros por pares (entrada/salida)
        current_employee = None
        check_in_time = None
        attendance_count = 0
        
        for log in time_logs:
            employee_id, timestamp, action = log
            
            if action.lower() == 'entrada':
                if current_employee == employee_id:
                    # Si hay una entrada sin salida, cerrar el registro anterior
                    if check_in_time:
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
        print("Migración completada exitosamente")
        
    except Exception as e:
        print(f"Error durante la migración: {str(e)}")
        new_conn.rollback()
    
    finally:
        old_conn.close()
        new_conn.close()

if __name__ == '__main__':
    migrate_database()
