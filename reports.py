import pandas as pd
from datetime import datetime, timedelta
import sqlite3
from config import Config
import os

def get_attendance_data(start_date=None, end_date=None):
    """Obtiene los datos de asistencia en el rango de fechas especificado."""
    conn = sqlite3.connect(Config.SQLITE_DB_PATH)
    
    query = """
    SELECT 
        e.name as Nombre,
        e.nfc_id as NFC_ID,
        date(t.timestamp) as Fecha,
        GROUP_CONCAT(CASE 
            WHEN t.action = 'check-in' THEN time(t.timestamp)
            ELSE NULL 
        END) as Entrada,
        GROUP_CONCAT(CASE 
            WHEN t.action = 'check-out' THEN time(t.timestamp)
            ELSE NULL 
        END) as Salida,
        CASE 
            WHEN COUNT(DISTINCT t.action) = 2 THEN 'Completo'
            WHEN MAX(t.action) = 'check-in' THEN 'Solo Entrada'
            WHEN MAX(t.action) = 'check-out' THEN 'Solo Salida'
            ELSE 'Sin Registro'
        END as Estado
    FROM employees e
    LEFT JOIN time_logs t ON e.id = t.employee_id
    """
    
    conditions = []
    params = []
    
    if start_date:
        conditions.append("date(t.timestamp) >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("date(t.timestamp) <= ?")
        params.append(end_date)
        
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
        
    query += """
    GROUP BY e.id, date(t.timestamp)
    ORDER BY e.name, date(t.timestamp)
    """
    
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def calculate_hours(row):
    """Calcula las horas trabajadas para una fila del reporte."""
    if pd.isna(row['Entrada']) or pd.isna(row['Salida']):
        return 0
    
    entrada = datetime.strptime(row['Entrada'], '%H:%M:%S')
    salida = datetime.strptime(row['Salida'], '%H:%M:%S')
    
    # Si la salida es anterior a la entrada, asumimos que es del día siguiente
    if salida < entrada:
        salida = salida + timedelta(days=1)
    
    diferencia = salida - entrada
    return round(diferencia.total_seconds() / 3600, 2)

def generate_gusto_report(start_date=None, end_date=None):
    """Genera un reporte en formato compatible con gusto.com."""
    df = get_attendance_data(start_date, end_date)
    
    # Calcular horas trabajadas
    df['Horas'] = df.apply(calculate_hours, axis=1)
    
    # Crear archivo Excel
    output_file = 'attendance_report.xlsx'
    writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
    
    # Hoja de resumen diario
    df_daily = df.copy()
    df_daily.to_excel(writer, sheet_name='Registro Diario', index=False)
    
    # Hoja de resumen por empleado
    df_summary = df.groupby('Nombre').agg({
        'Horas': 'sum',
        'Estado': lambda x: (x == 'Completo').sum()
    }).reset_index()
    df_summary.columns = ['Nombre', 'Total Horas', 'Días Completos']
    df_summary.to_excel(writer, sheet_name='Resumen', index=False)
    
    # Formato para gusto.com
    df_gusto = df[['Nombre', 'Fecha', 'Entrada', 'Salida', 'Horas']].copy()
    df_gusto['Fecha'] = pd.to_datetime(df_gusto['Fecha']).dt.strftime('%Y-%m-%d')
    df_gusto.columns = ['Employee Name', 'Date', 'Clock In', 'Clock Out', 'Hours']
    df_gusto.to_excel(writer, sheet_name='Gusto Format', index=False)
    
    # Dar formato al archivo
    workbook = writer.book
    
    # Formato para números
    num_format = workbook.add_format({'num_format': '0.00'})
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    time_format = workbook.add_format({'num_format': 'hh:mm:ss'})
    
    # Aplicar formatos a cada hoja
    for sheet_name in writer.sheets:
        worksheet = writer.sheets[sheet_name]
        worksheet.set_column('A:Z', 15)  # Ancho de columnas
        
        # Aplicar formatos específicos según la hoja
        if sheet_name in ['Registro Diario', 'Gusto Format']:
            worksheet.set_column('C:D', 15, time_format)  # Formato de hora
            worksheet.set_column('E:E', 12, num_format)   # Formato de horas
    
    writer.close()
    return output_file
