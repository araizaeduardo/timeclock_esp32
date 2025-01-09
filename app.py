from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash, g, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect
import sqlite3
from datetime import datetime, timedelta
import logging
from config import Config
import functools
from reports import generate_gusto_report
import os
import telnyx
from apscheduler.schedulers.background import BackgroundScheduler
import hashlib
from flask import Response
import json
import time

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'dev'  # Clave temporal para desarrollo
csrf = CSRFProtect(app)

# Configuración de Telnyx
telnyx.api_key = os.getenv('TELNYX_API_KEY')
TELNYX_PHONE_NUMBER = os.getenv('TELNYX_PHONE_NUMBER')

# Configuración de logging
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

@app.template_filter('time_diff')
def time_diff_filter(time1, time2):
    """Calcular diferencia en minutos entre dos horas (formato HH:MM)."""
    try:
        t1 = time1.split(':')
        t2 = time2.split(':')
        minutes1 = int(t1[0]) * 60 + int(t1[1])
        minutes2 = int(t2[0]) * 60 + int(t2[1])
        return abs(minutes1 - minutes2)
    except:
        return 0

@app.template_filter('timestamp')
def timestamp_filter(date_str):
    """Convertir string de fecha o datetime a timestamp."""
    if isinstance(date_str, datetime):
        return date_str.timestamp()
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').timestamp()

def init_db():
    """Inicializar la base de datos."""
    conn = get_db()
    with open('schema.sql', 'r') as f:
        conn.executescript(f.read())
    conn.commit()

@app.cli.command('init-db')
def init_db_command():
    """Comando para inicializar la base de datos."""
    init_db()
    print('Base de datos inicializada.')

def get_db():
    """Conectar a la base de datos."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            'timeclock.db',
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(error):
    """Cerrar la conexión a la base de datos."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if 'employee_id' not in session and 'admin_id' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        print(f"Session: {session}")  # Debug
        if 'admin_id' not in session:
            flash('Acceso denegado. Por favor inicie sesión como administrador.')
            return redirect(url_for('index'))
        return view(**kwargs)
    return wrapped_view

def render_menu():
    """Helper to render the menu based on user role."""
    menu = []
    if 'admin_id' in session:
        menu.append({'name': 'Dashboard', 'url': url_for('dashboard')})
        menu.append({'name': 'Administración', 'url': url_for('admin')})
        menu.append({'name': 'Reportes', 'url': url_for('reports')})
        menu.append({'name': 'Cerrar Sesión', 'url': url_for('logout')})
    elif 'employee_id' in session:
        menu.append({'name': 'Mi Perfil', 'url': url_for('employee_profile')})
        menu.append({'name': 'Cerrar Sesión', 'url': url_for('logout')})
    return menu

@app.context_processor
def inject_menu():
    """Inject the menu into the templates."""
    return {'menu': render_menu()}

@app.route('/')
def index():
    """Página principal con check-in/check-out."""
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        nfc_id = request.form.get('nfc_id')
        password = request.form.get('password')
        
        if not nfc_id:
            flash('Por favor ingrese su ID')
            return redirect(url_for('index'))
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Primero intentar login como admin
        if password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            logger.debug(f"Login attempt - ID: {nfc_id}, Hash: {hashed_password}")  # Debug
            
            cursor.execute('SELECT id, username FROM admins WHERE username = ? AND password = ?',
                          (nfc_id, hashed_password))
            admin = cursor.fetchone()
            
            if admin:
                session.clear()
                session['admin_id'] = admin[0]
                session['admin_username'] = admin[1]
                return redirect(url_for('dashboard'))
        
        # Si no es admin o no proporcionó contraseña, intentar login como empleado
        cursor.execute('SELECT id, name, password FROM employees WHERE nfc_id = ?', (nfc_id,))
        employee = cursor.fetchone()
        
        if employee and password:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            if hashed_password == employee[2]:
                session.clear()
                session['employee_id'] = employee[0]
                session['employee_name'] = employee[1]
                return redirect(url_for('employee_profile'))
        
        flash('ID o contraseña incorrectos')
        return redirect(url_for('index'))
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@admin_required
def dashboard():
    conn = get_db()
    cursor = conn.cursor()
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT 
            e.name,
            a.check_in,
            a.check_out,
            e.schedule_in,
            e.schedule_out,
            e.department
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE DATE(a.check_in) = DATE('now')
        ORDER BY a.check_in DESC
    ''')
    today_records = cursor.fetchall()
    
    cursor.execute('''
        SELECT COUNT(*) 
        FROM employees 
        WHERE is_active = 1
    ''')
    total_employees = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(DISTINCT employee_id) 
        FROM attendance 
        WHERE DATE(check_in) = DATE('now')
    ''')
    present_today = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT COUNT(*) 
        FROM attendance 
        WHERE DATE(check_in) = DATE('now')
        AND check_out IS NULL
    ''')
    currently_in = cursor.fetchone()[0]
    
    cursor.execute('''
        SELECT 
            e.name,
            a.check_in,
            e.schedule_in
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE DATE(a.check_in) = DATE('now')
        AND TIME(a.check_in) > TIME(e.schedule_in, '+15 minutes')
        ORDER BY a.check_in DESC
    ''')
    late_arrivals = cursor.fetchall()
    
    return render_template('dashboard.html',
                         today_records=today_records,
                         total_employees=total_employees,
                         present_today=present_today,
                         currently_in=currently_in,
                         late_arrivals=late_arrivals,
                         current_date=current_date)

@app.route('/admin')
@admin_required
def admin():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            e.id,
            e.name,
            e.nfc_id,
            e.department,
            e.schedule_in,
            e.schedule_out,
            e.is_active,
            (SELECT COUNT(*) FROM attendance a WHERE a.employee_id = e.id) as attendance_count
        FROM employees e
        ORDER BY e.name
    ''')
    employees = cursor.fetchall()
    
    return render_template('admin.html', 
                         employees=employees,
                         current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

@app.route('/register_employee', methods=['POST'])
@admin_required
def register_employee():
    try:
        if not request.is_json:
            return jsonify({'error': 'Se requiere JSON'}), 400
            
        data = request.get_json()
        name = data.get('name')
        nfc_id = data.get('nfc_id')
        phone = data.get('phone', '')
        department = data.get('department', '')
        schedule_in = data.get('schedule_in', '09:00')
        schedule_out = data.get('schedule_out', '18:00')
        
        # Validar campos requeridos
        if not all([name, nfc_id, schedule_in, schedule_out]):
            return jsonify({'error': 'Los campos nombre, NFC ID, hora de entrada y hora de salida son requeridos'}), 400
        
        # Generar contraseña inicial (apellido en minúsculas)
        last_name = name.split()[-1].lower()
        password = hashlib.sha256(last_name.encode()).hexdigest()
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO employees (
                name, nfc_id, password, phone, department,
                schedule_in, schedule_out, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        ''', (name, nfc_id.upper(), password, phone, department, schedule_in, schedule_out))
        
        conn.commit()
        
        return jsonify({
            'message': 'Empleado registrado exitosamente',
            'password': last_name
        })
        
    except sqlite3.IntegrityError:
        return jsonify({'error': 'El ID de NFC ya está registrado'}), 400
    except Exception as e:
        logger.error(f"Error registrando empleado: {str(e)}")
        return jsonify({'error': 'Error registrando empleado'}), 500

@app.route('/delete_employee/<int:employee_id>', methods=['POST'])
@admin_required
def delete_employee(employee_id):
    cursor = get_db().cursor()
    
    cursor.execute('DELETE FROM time_logs WHERE employee_id = ?', (employee_id,))
    
    cursor.execute('DELETE FROM employees WHERE id = ?', (employee_id,))
    get_db().commit()
    
    flash('Empleado eliminado exitosamente', 'success')
    return redirect(url_for('admin'))

def validate_attendance(employee_id, action):
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT action, timestamp 
            FROM time_logs 
            WHERE employee_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ''', (employee_id,))
        last_record = cursor.fetchone()
        
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if action == 'check-in':
            cursor.execute('''
                SELECT COUNT(*) 
                FROM time_logs 
                WHERE employee_id = ? 
                AND action = 'check-in' 
                AND datetime(timestamp) >= datetime(?)
            ''', (employee_id, today_start.isoformat()))
            
            check_ins_today = cursor.fetchone()[0]
            
            if check_ins_today > 0:
                return False, "Ya realizaste el check-in hoy. Debes hacer check-out primero."
                
        elif action == 'check-out':
            if not last_record:
                return False, "Debes hacer check-in antes de poder hacer check-out."
                
            last_action, last_timestamp = last_record
            last_time = datetime.fromisoformat(last_timestamp)
            
            if last_action == 'check-out':
                return False, "Ya realizaste el check-out. Debes hacer check-in primero."
                
            if last_action == 'check-in':
                if last_time > now:
                    return False, "Error: La hora de salida no puede ser anterior a la hora de entrada."
                
                if last_time.date() < now.date():
                    hours_diff = (now - last_time).total_seconds() / 3600
                    if hours_diff > 24:
                        return False, "Han pasado más de 24 horas desde tu check-in. Por favor, contacta a tu supervisor."
        
        return True, None
        
    except Exception as e:
        logger.error(f"Error validando asistencia: {str(e)}")
        return False, "Error interno validando la asistencia."

@app.route('/log_nfc/<nfc_id>', methods=['POST'])
@csrf.exempt  # Exento de CSRF para permitir lecturas NFC externas
def log_nfc(nfc_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM employees WHERE nfc_id = ?', (nfc_id,))
        employee = cursor.fetchone()

        if not employee:
            logger.warning(f"Intento de registro con NFC no registrado: {nfc_id}")
            return jsonify({'error': 'Tarjeta NFC no registrada'}), 404

        employee_dict = {
            'id': employee[0],
            'name': employee[1],
            'nfc_id': employee[2],
            'is_active': employee[3]
        }

        if not employee_dict['is_active']:
            return jsonify({'error': 'Empleado inactivo'}), 403

        action = 'check-in' if request.form.get('action') == 'in' else 'check-out'
        signature = request.form.get('signature')
        signature_image = request.form.get('signature_image')
        
        if not signature or not signature_image:
            return jsonify({'error': 'Se requiere firma para registrar asistencia'}), 400

        is_valid, error_message = validate_attendance(employee_dict['id'], action)
        if not is_valid:
            logger.warning(f"Validación fallida para {employee_dict['name']}: {error_message}")
            return jsonify({'error': error_message}), 400

        cursor.execute(
            'INSERT INTO time_logs (employee_id, timestamp, action, signature, signature_image) VALUES (?, ?, ?, ?, ?)',
            (employee_dict['id'], datetime.now().isoformat(), action, signature, signature_image)
        )
        conn.commit()
        
        logger.info(f"{action.capitalize()} registrado para {employee_dict['name']}")
        return jsonify({
            'message': f'{action.capitalize()} registrado exitosamente para {employee_dict["name"]}.',
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error en log_nfc: {str(e)}")
        conn.rollback()
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/get_employee/<nfc_id>')
def get_employee(nfc_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM employees WHERE nfc_id = ?', (nfc_id,))
        employee = cursor.fetchone()

        if not employee:
            return jsonify({'error': 'Empleado no encontrado'}), 404

        return jsonify({'name': employee[0]})

    except Exception as e:
        logger.error(f"Error en get_employee: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500

@app.route('/reports')
@admin_required
def reports():
    return render_template('reports.html')

@app.route('/generate_report', methods=['POST'])
@admin_required
def generate_report():
    try:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        output_file = generate_gusto_report(start_date, end_date)
        
        return send_file(
            output_file,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'attendance_report_{start_date}_to_{end_date}.xlsx'
        )
    except Exception as e:
        logger.error(f"Error generando reporte: {str(e)}")
        flash('Error al generar el reporte', 'danger')
        return redirect(url_for('reports'))

@app.route('/get_attendance_data')
@admin_required
def get_attendance_data():
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener los registros del último mes
    cursor.execute('''
        SELECT 
            e.name,
            a.check_in,
            a.check_out,
            e.schedule_in,
            e.schedule_out,
            e.department
        FROM attendance a
        JOIN employees e ON a.employee_id = e.id
        WHERE a.check_in >= date('now', '-30 days')
        ORDER BY a.check_in DESC
    ''')
    
    records = cursor.fetchall()
    attendance_data = []
    
    for record in records:
        attendance_data.append({
            'name': record[0],
            'check_in': record[1],
            'check_out': record[2] if record[2] else None,
            'schedule_in': record[3],
            'schedule_out': record[4],
            'department': record[5]
        })
    
    return jsonify(attendance_data)

@app.route('/toggle_employee_status/<int:employee_id>', methods=['POST'])
@admin_required
def toggle_employee_status(employee_id):
    if not session.get('is_admin'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('dashboard'))
        
    cursor = get_db().cursor()
    
    cursor.execute('SELECT is_active FROM employees WHERE id = ?', (employee_id,))
    result = cursor.fetchone()
    
    if result:
        new_status = 0 if result[0] else 1
        cursor.execute('UPDATE employees SET is_active = ? WHERE id = ?', (new_status, employee_id))
        get_db().commit()
        
        status_text = 'activado' if new_status else 'desactivado'
        flash(f'Empleado {status_text} exitosamente', 'success')
    else:
        flash('Empleado no encontrado', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/employee_report/<int:employee_id>')
@admin_required
def employee_report(employee_id):
    if not session.get('is_admin'):
        flash('Acceso no autorizado', 'danger')
        return redirect(url_for('dashboard'))
        
    cursor = get_db().cursor()
    
    cursor.execute('SELECT * FROM employees WHERE id = ?', (employee_id,))
    employee = cursor.fetchone()
    
    if not employee:
        flash('Empleado no encontrado', 'danger')
        return redirect(url_for('admin'))
    
    cursor.execute('''
        SELECT date(timestamp), 
               MIN(CASE WHEN action = 'check-in' THEN time(timestamp) END) as check_in,
               MAX(CASE WHEN action = 'check-out' THEN time(timestamp) END) as check_out,
               ROUND(
                   (JULIANDAY(MAX(CASE WHEN action = 'check-out' THEN timestamp END)) - 
                    JULIANDAY(MIN(CASE WHEN action = 'check-in' THEN timestamp END))) * 24,
                   1
               ) as hours
        FROM time_logs
        WHERE employee_id = ?
        GROUP BY date(timestamp)
        ORDER BY date(timestamp) DESC
    ''', (employee_id,))
    
    logs = []
    for row in cursor.fetchall():
        if row[0]:  
            logs.append({
                'date': row[0],
                'check_in': str(row[1]) if row[1] else None,
                'check_out': str(row[2]) if row[2] else None,
                'hours': float(row[3]) if row[3] else None
            })
    
    return render_template('employee_report.html', employee=employee, logs=logs)

@app.route('/read_nfc', methods=['POST'])
def read_nfc():
    try:
        data = request.get_json()
        if not data or 'uid' not in data:
            logger.error("Datos NFC inválidos recibidos")
            return jsonify({'error': 'Datos inválidos'}), 400
            
        nfc_id = data['uid']
        logger.info(f"NFC ID recibido del ESP32: {nfc_id}")
        
        result = log_nfc(nfc_id)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error procesando lectura NFC: {str(e)}")
        return jsonify({'error': str(e)}), 500

def send_sms_reminder(phone_number, employee_name):
    try:
        if phone_number.startswith('0'):
            phone_number = '+52' + phone_number[1:]
        elif not phone_number.startswith('+'):
            phone_number = '+52' + phone_number

        message = telnyx.Message.create(
            from_=TELNYX_PHONE_NUMBER,
            to=phone_number,
            text=f'Hola {employee_name}, parece que olvidaste marcar tu salida. Por favor, recuerda hacerlo al terminar tu jornada.'
        )
        logger.info(f"SMS enviado a {employee_name}: {message.id}")
        return True
    except Exception as e:
        logger.error(f"Error enviando SMS a {employee_name}: {str(e)}")
        return False

def check_missing_checkouts():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        eight_hours_ago = datetime.now() - timedelta(hours=8)
        
        cursor.execute('''
            SELECT e.name, e.phone
            FROM employees e
            JOIN attendance a ON e.id = a.employee_id
            WHERE a.check_in <= ? 
            AND a.check_out IS NULL
            AND e.is_active = 1
            AND e.phone IS NOT NULL
        ''', (eight_hours_ago,))
        
        results = cursor.fetchall()
        
        for name, phone in results:
            if phone:
                send_sms_reminder(phone, name)
        
    except Exception as e:
        logger.error(f"Error checking missing checkouts: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(check_missing_checkouts, 'interval', minutes=15)
scheduler.start()

@app.route('/check', methods=['POST'])
@csrf.exempt
def check():
    if request.method == 'POST':
        data = request.get_json()
        nfc_id = data.get('nfc_id')
        action = data.get('action')  # 'check-in' o 'check-out'
        
        if not nfc_id:
            return jsonify({'success': False, 'message': 'ID de empleado no proporcionado'}), 400
        
        conn = get_db()
        cursor = conn.cursor()
        
        try:
            # Iniciar transacción
            cursor.execute('BEGIN EXCLUSIVE TRANSACTION')
            
            # Obtener información del empleado
            cursor.execute('SELECT id, name FROM employees WHERE nfc_id = ?', (nfc_id,))
            employee = cursor.fetchone()
            
            if not employee:
                cursor.execute('ROLLBACK')
                return jsonify({'success': False, 'message': 'Empleado no encontrado'}), 404
            
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')
            today_str = now.strftime('%Y-%m-%d')
            
            # Obtener el último registro del día para este empleado
            cursor.execute('''
                SELECT id, check_in, check_out 
                FROM attendance 
                WHERE employee_id = ? 
                AND DATE(check_in) = ? 
                ORDER BY check_in DESC 
                LIMIT 1
            ''', (employee[0], today_str))
            
            last_record = cursor.fetchone()
            
            if action == 'check-in':
                if last_record and last_record[2] is None:
                    # Si hay un registro hoy y no tiene check_out, no permitir otro check-in
                    cursor.execute('ROLLBACK')
                    return jsonify({
                        'success': False,
                        'message': 'Ya tienes un check-in activo para hoy. Debes hacer check-out primero.'
                    }), 400
                
                # Registrar nuevo check-in
                cursor.execute('''
                    INSERT INTO attendance (employee_id, check_in)
                    VALUES (?, ?)
                ''', (employee[0], now_str))
                message = f'Bienvenido {employee[1]}, entrada registrada a las {now.strftime("%H:%M")}'
                
            else:  # check-out
                if not last_record or last_record[2] is not None:
                    # Si no hay registro hoy o el último registro ya tiene check_out
                    cursor.execute('ROLLBACK')
                    return jsonify({
                        'success': False,
                        'message': 'No tienes un check-in activo para hoy. Debes hacer check-in primero.'
                    }), 400
                
                # Registrar check-out
                cursor.execute('''
                    UPDATE attendance 
                    SET check_out = ? 
                    WHERE id = ? 
                    AND check_out IS NULL
                ''', (now_str, last_record[0]))
                message = f'Hasta luego {employee[1]}, salida registrada a las {now.strftime("%H:%M")}'
            
            # Confirmar transacción
            cursor.execute('COMMIT')
            
            return jsonify({
                'success': True,
                'message': message,
                'employee_name': employee[1],
                'action': action,
                'timestamp': now_str
            })
            
        except Exception as e:
            # Si hay cualquier error, hacer rollback
            cursor.execute('ROLLBACK')
            return jsonify({
                'success': False,
                'message': f'Error al procesar la solicitud: {str(e)}'
            }), 500

@app.route('/edit_employee/<int:employee_id>', methods=['GET'])
@admin_required
def edit_employee(employee_id):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, name, nfc_id, department, schedule_in, schedule_out, phone, is_active
        FROM employees 
        WHERE id = ?
    ''', (employee_id,))
    employee = cursor.fetchone()
    
    if employee:
        return jsonify({
            'id': employee[0],
            'name': employee[1],
            'nfc_id': employee[2],
            'department': employee[3],
            'schedule_in': employee[4],
            'schedule_out': employee[5],
            'phone': employee[6],
            'is_active': employee[7]
        })
    return jsonify({'error': 'Empleado no encontrado'}), 404

@app.route('/update_employee/<int:employee_id>', methods=['POST'])
@admin_required
def update_employee(employee_id):
    if not request.is_json:
        return jsonify({'error': 'Se requiere JSON'}), 400
    
    data = request.get_json()
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            UPDATE employees 
            SET name = ?,
                nfc_id = ?,
                department = ?,
                schedule_in = ?,
                schedule_out = ?,
                phone = ?,
                is_active = ?
            WHERE id = ?
        ''', (
            data.get('name'),
            data.get('nfc_id'),
            data.get('department'),
            data.get('schedule_in'),
            data.get('schedule_out'),
            data.get('phone'),
            1 if data.get('is_active') else 0,
            employee_id
        ))
        conn.commit()
        return jsonify({'message': 'Empleado actualizado correctamente'})
    except sqlite3.IntegrityError:
        conn.rollback()
        return jsonify({'error': 'El ID de NFC ya está en uso'}), 400
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/esp32-events')
def esp32_events():
    def generate():
        while True:
            # Esperar por datos del ESP32
            if 'esp32_data' in app.config:
                data = app.config.pop('esp32_data')
                yield f"data: {json.dumps(data)}\n\n"
            time.sleep(1)
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/esp32-data', methods=['POST'])
def esp32_data():
    data = request.get_json()
    if not data or 'nfc_id' not in data:
        return jsonify({
            'success': False,
            'message': 'Datos inválidos',
            'led_color': 'red',
            'beep': True
        }), 400
    
    # Obtener información del empleado
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, name, schedule_in, schedule_out 
        FROM employees 
        WHERE nfc_id = ?
    ''', (data['nfc_id'],))
    employee = cursor.fetchone()
    
    if not employee:
        return jsonify({
            'success': False,
            'message': 'Empleado no encontrado',
            'led_color': 'red',
            'beep': True
        }), 404
    
    # Determinar si es check-in o check-out basado en el horario del empleado
    now = datetime.now()
    schedule_in = datetime.strptime(employee[2], '%H:%M').time()
    schedule_out = datetime.strptime(employee[3], '%H:%M').time()
    current_time = now.time()
    
    # Si está más cerca de la hora de entrada, es check-in
    time_to_in = abs((datetime.combine(now.date(), current_time) - 
                     datetime.combine(now.date(), schedule_in)).total_seconds())
    time_to_out = abs((datetime.combine(now.date(), current_time) - 
                      datetime.combine(now.date(), schedule_out)).total_seconds())
    
    action = 'check-in' if time_to_in < time_to_out else 'check-out'
    
    # Verificar si ya registró entrada/salida
    cursor.execute('''
        SELECT check_in, check_out 
        FROM attendance 
        WHERE employee_id = ? AND DATE(check_in) = DATE(?)
        ORDER BY check_in DESC LIMIT 1
    ''', (employee[0], now))
    last_record = cursor.fetchone()
    
    # Lógica para determinar si se permite el registro
    if action == 'check-in':
        if last_record and not last_record[1]:
            return jsonify({
                'success': False,
                'message': 'Ya registraste entrada. Debes registrar salida primero.',
                'led_color': 'yellow',
                'beep': True
            }), 400
    else:  # check-out
        if not last_record or last_record[1]:
            return jsonify({
                'success': False,
                'message': 'Debes registrar entrada primero.',
                'led_color': 'yellow',
                'beep': True
            }), 400
    
    # Registrar la asistencia
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    if action == 'check-in':
        cursor.execute('''
            INSERT INTO attendance (employee_id, check_in)
            VALUES (?, ?)
        ''', (employee[0], now_str))
        message = f'Bienvenido {employee[1]}'
    else:
        cursor.execute('''
            UPDATE attendance 
            SET check_out = ? 
            WHERE employee_id = ? AND DATE(check_in) = DATE(?) AND check_out IS NULL
        ''', (now_str, employee[0], now_str))
        
        if cursor.rowcount > 0:
            message = f'Hasta luego {employee[1]}'
        else:
            return jsonify({
                'success': False, 
                'message': 'No se encontró un registro de entrada sin salida para hoy'
            }), 400
    
    conn.commit()
    
    # Determinar si llegó tarde
    is_late = False
    if action == 'check-in':
        grace_period = timedelta(minutes=15)
        scheduled_time = datetime.combine(now.date(), schedule_in)
        is_late = now > scheduled_time + grace_period
    
    response_data = {
        'success': True,
        'message': message,
        'led_color': 'red' if is_late else 'green',
        'beep': is_late,
        'display_text': f'{message}\n{"TARDE" if is_late else "A TIEMPO"}'
    }
    
    # Almacenar para SSE
    app.config['esp32_data'] = {
        'nfc_id': data['nfc_id'],
        'action': action,
        'message': message,
        'timestamp': now_str
    }
    
    return jsonify(response_data)

@app.route('/employee/profile')
@login_required
def employee_profile():
    # Verificar que sea un empleado
    if 'employee_id' not in session:
        flash('Esta página es solo para empleados', 'error')
        return redirect(url_for('index'))
    
    conn = get_db()
    cursor = conn.cursor()
    
    # Obtener información del empleado
    cursor.execute('''
        SELECT name, department, schedule_in, schedule_out 
        FROM employees 
        WHERE id = ?
    ''', (session['employee_id'],))
    employee_row = cursor.fetchone()
    
    if not employee_row:
        flash('No se encontró la información del empleado', 'error')
        return redirect(url_for('index'))
    
    employee = {
        'name': employee_row[0],
        'department': employee_row[1],
        'schedule_in': employee_row[2],
        'schedule_out': employee_row[3]
    }
    
    # Obtener estado actual (registro de hoy)
    cursor.execute('''
        SELECT check_in, check_out
        FROM attendance 
        WHERE employee_id = ? AND DATE(check_in) = DATE('now')
        ORDER BY check_in DESC LIMIT 1
    ''', (session['employee_id'],))
    current_status_row = cursor.fetchone()
    
    current_status = None
    if current_status_row:
        check_in = current_status_row[0]
        check_out = current_status_row[1]
        
        # Convertir a datetime si son strings
        if isinstance(check_in, str):
            check_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
        if check_out and isinstance(check_out, str):
            check_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
        
        # Calcular horas trabajadas
        if check_out:
            hours_worked = (check_out - check_in).total_seconds() / 3600
        else:
            hours_worked = (datetime.now() - check_in).total_seconds() / 3600
        
        # Verificar si llegó a tiempo
        schedule_in_time = datetime.strptime(employee['schedule_in'], '%H:%M').time()
        check_in_time = check_in.time()
        on_time = check_in_time <= schedule_in_time
            
        current_status = {
            'check_in': check_in,
            'check_out': check_out,
            'hours_worked': hours_worked,
            'on_time': on_time
        }
    
    # Obtener historial de asistencia
    start_date = request.args.get('start_date', 
                                (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    cursor.execute('''
        SELECT check_in, check_out
        FROM attendance 
        WHERE employee_id = ? 
        AND DATE(check_in) BETWEEN ? AND ?
        ORDER BY check_in DESC
    ''', (session['employee_id'], start_date, end_date))
    attendance_rows = cursor.fetchall()
    
    attendance_records = []
    for row in attendance_rows:
        check_in = row[0]
        check_out = row[1]
        
        # Convertir a datetime si son strings
        if isinstance(check_in, str):
            check_in = datetime.strptime(check_in, '%Y-%m-%d %H:%M:%S')
        if check_out and isinstance(check_out, str):
            check_out = datetime.strptime(check_out, '%Y-%m-%d %H:%M:%S')
            
        attendance_records.append({
            'check_in': check_in,
            'check_out': check_out
        })
    
    return render_template('employee_profile.html',
                         employee=employee,
                         current_status=current_status,
                         attendance_records=attendance_records)

if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(host='0.0.0.0', port=5007, debug=True)
