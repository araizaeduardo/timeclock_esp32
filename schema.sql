-- Tabla de empleados
DROP TABLE IF EXISTS attendance;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS admins;

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    nfc_id TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    department TEXT,
    schedule_in TEXT NOT NULL DEFAULT '09:00',
    schedule_out TEXT NOT NULL DEFAULT '18:00',
    phone TEXT,
    is_active INTEGER NOT NULL DEFAULT 1
);

-- Tabla de asistencia
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    check_in TIMESTAMP NOT NULL,
    check_out TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees (id)
);

-- Tabla de administradores
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
);

-- Tabla de configuración
CREATE TABLE IF NOT EXISTS config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default admin
INSERT INTO admins (username, password) VALUES ('admin', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918');

-- Insert sample employees with hashed passwords (password = apellido en minúsculas)
INSERT INTO employees (name, nfc_id, password, department, schedule_in, schedule_out) 
VALUES 
('Juan Pérez', '04A5B9C2', '05846abb5a0a9d9648deb49f11891bddb5f0056a91d2b3c9e5f7b64b4e1d2c9a', 'Ventas', '09:00', '18:00'),
('María García', '14B5C9D2', '3b6c4cf6a644a989d2ef71e81b2261c8d147d0cc75cc0ae8e8b79d56c1ead8a1', 'Marketing', '08:00', '17:00'),
('Carlos López', '24C5D9E2', '4b2e98bc7972d699b2516bca474c8c5f716bb6a6f5ec9c5f4d5b92d8997fde2f', 'IT', '10:00', '19:00'),
('Eduardo', '123465', '71eaea56f7f31be16276ab904b8b04144daf720badab79d5cf291edbbfa950fd', 'IT', '11:00', '19:00');