
from flask import Flask, render_template, request, redirect, url_for, session, flash, make_response
from flask_mysqldb import MySQL
import MySQLdb.cursors
import io
import csv
import pandas as pd
from config import Config  # Importamos la configuración


app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)


# Ruta de Login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        query = "SELECT * FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            session['role'] = account['role']
            return redirect(url_for('dashboard'))
        else:
            flash('Nombre de usuario o contraseña incorrectos.')
    return render_template('login.html')


# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        return render_template('dashboard.html')
    return redirect(url_for('login'))


# Empleados
@app.route('/empleados')
def empleados():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, cedula, nombre, apellido FROM empleados")
        empleados = cursor.fetchall()
        return render_template('empleados.html', empleados=empleados)
    return redirect(url_for('login'))


# Asistencias (con filtros)
@app.route('/asistencias', methods=['GET', 'POST'])
def asistencias():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        filters = []
        params = []
        if request.method == 'POST':
            fecha_inicio = request.form.get('fecha_inicio')
            fecha_fin = request.form.get('fecha_fin')
            empleado = request.form.get('empleado')
            if fecha_inicio:
                filters.append("a.fecha >= %s")
                params.append(fecha_inicio)
            if fecha_fin:
                filters.append("a.fecha <= %s")
                params.append(fecha_fin)
            if empleado:
                filters.append("(e.nombre LIKE %s OR e.apellido LIKE %s OR e.cedula LIKE %s)")
                search = "%" + empleado + "%"
                params.extend([search, search, search])

        query = """
            SELECT a.id, e.nombre, e.apellido, a.fecha, a.tipo
            FROM asistencia AS a
            INNER JOIN empleados AS e ON a.empleado_id = e.id
        """
        if filters:
            query += " WHERE " + " AND ".join(filters)
        query += " ORDER BY a.fecha DESC"
        cursor.execute(query, tuple(params))
        asistencias = cursor.fetchall()
        return render_template('asistencias.html', asistencias=asistencias)
    return redirect(url_for('login'))


# Exportar Empleados a CSV
@app.route('/export_empleados_csv')
def export_empleados_csv():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, cedula, nombre, apellido FROM empleados")
        empleados = cursor.fetchall()

        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['ID', 'Cédula', 'Nombre', 'Apellido'])
        for emp in empleados:
            cw.writerow([emp['id'], emp['cedula'], emp['nombre'], emp['apellido']])
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=empleados.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    return redirect(url_for('login'))


# Exportar Empleados a Excel
@app.route('/export_empleados_excel')
def export_empleados_excel():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, cedula, nombre, apellido FROM empleados")
        empleados = cursor.fetchall()

        df = pd.DataFrame(empleados)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Empleados')
        output.seek(0)
        response = make_response(output.read())
        response.headers["Content-Disposition"] = "attachment; filename=empleados.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    return redirect(url_for('login'))


# Exportar Asistencias a CSV
@app.route('/export_asistencias_csv')
def export_asistencias_csv():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        query = """
            SELECT a.id, e.nombre, e.apellido, a.fecha, a.tipo
            FROM asistencia AS a
            INNER JOIN empleados AS e ON a.empleado_id = e.id
            ORDER BY a.fecha DESC
        """
        cursor.execute(query)
        asistencias = cursor.fetchall()

        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['ID', 'Empleado', 'Fecha', 'Tipo'])
        for a in asistencias:
            empleado_nombre = f"{a['nombre']} {a['apellido']}"
            cw.writerow([a['id'], empleado_nombre, a['fecha'], a['tipo']])
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=asistencias.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    return redirect(url_for('login'))


# Exportar Asistencias a Excel
@app.route('/export_asistencias_excel')
def export_asistencias_excel():
    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        query = """
            SELECT a.id, CONCAT(e.nombre, ' ', e.apellido) AS empleado, a.fecha, a.tipo
            FROM asistencia AS a
            INNER JOIN empleados AS e ON a.empleado_id = e.id
            ORDER BY a.fecha DESC
        """
        cursor.execute(query)
        asistencias = cursor.fetchall()

        df = pd.DataFrame(asistencias)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Asistencias')
        output.seek(0)
        response = make_response(output.read())
        response.headers["Content-Disposition"] = "attachment; filename=asistencias.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    return redirect(url_for('login'))


# Cerrar sesión
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)