import sqlite3
import os
import hashlib

def init_admin():
    print("Iniciando creación del administrador...")
    
    # Conectar a la base de datos
    conn = sqlite3.connect('timeclock.db')
    cursor = conn.cursor()
    
    try:
        # Crear tabla de administradores si no existe
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        ''')
        
        # Crear admin por defecto
        username = 'admin'
        password = 'admin123'  # Contraseña por defecto
        
        # Hashear la contraseña
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        # Insertar admin
        cursor.execute('''
            INSERT OR REPLACE INTO admins (username, password, name, email)
            VALUES (?, ?, ?, ?)
        ''', (username, hashed_password, 'Administrador', 'admin@example.com'))
        
        conn.commit()
        print(f"\nAdministrador creado exitosamente!")
        print(f"Usuario: {username}")
        print(f"Contraseña: {password}")
        print("\nPor favor, cambia la contraseña después de iniciar sesión.")
        
    except Exception as e:
        print(f"\nError durante la creación del administrador: {str(e)}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == '__main__':
    init_admin()
