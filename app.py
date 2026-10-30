from flask import Flask, request, jsonify, session, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
from datetime import datetime
import sqlite3, os

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'vahanashare.db'
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-before-deployment')
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')


def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def init_db():
    with db() as con:
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS vehicles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, category TEXT NOT NULL, model TEXT NOT NULL,
            price REAL NOT NULL, location TEXT NOT NULL, image TEXT DEFAULT '',
            description TEXT DEFAULT '', available INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            vehicle_id INTEGER NOT NULL REFERENCES vehicles(id),
            start_date TEXT NOT NULL, end_date TEXT NOT NULL,
            total REAL NOT NULL, status TEXT NOT NULL DEFAULT 'Confirmed',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            message TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            is_read INTEGER NOT NULL DEFAULT 0
        );
        ''')
        admin = con.execute('SELECT id FROM users WHERE email=?', ('admin@vahanashare.com',)).fetchone()
        if not admin:
            con.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',
                        ('Administrator','admin@vahanashare.com',generate_password_hash('Admin123!'),'admin'))
        count = con.execute('SELECT COUNT(*) AS n FROM vehicles').fetchone()['n']
        if count == 0:
            samples = [
                ('Honda Activa 6G','Scooter','2024',350,'College Main Gate','🛵','Comfortable scooter for daily travel.'),
                ('Royal Enfield Classic 350','Bike','2023',700,'City Centre','🏍️','Classic motorcycle for longer rides.'),
                ('Yamaha FZ','Bike','2024',550,'North Parking','🏍️','Easy-to-handle street bike.'),
                ('Maruti Swift','Car','2022',1800,'Community Parking','🚗','Compact car suitable for city trips.'),
                ('Hyundai i20','Car','2023',2200,'South Gate','🚙','Comfortable hatchback with spacious interior.'),
                ('TVS Jupiter','Scooter','2024',320,'College Main Gate','🛵','Practical scooter for short journeys.')
            ]
            con.executemany('INSERT INTO vehicles(name,category,model,price,location,image,description) VALUES(?,?,?,?,?,?,?)', samples)


def current_user():
    if not session.get('user_id'): return None
    with db() as con:
        row = con.execute('SELECT id,name,email,role FROM users WHERE id=?', (session['user_id'],)).fetchone()
        return dict(row) if row else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user(): return jsonify({'error':'Please log in first.'}), 401
        return fn(*args, **kwargs)
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user: return jsonify({'error':'Please log in first.'}), 401
        if user['role'] != 'admin': return jsonify({'error':'Administrator access required.'}), 403
        return fn(*args, **kwargs)
    return wrapper


@app.get('/')
def home(): return render_template('index.html')

@app.get('/api/me')
def me(): return jsonify({'user': current_user()})

@app.post('/api/register')
def register():
    data = request.get_json(silent=True) or {}
    name, email, password = (str(data.get(k,'')).strip() for k in ('name','email','password'))
    if not name or not email or len(password) < 6:
        return jsonify({'error':'Enter your name, a valid email and a password of at least 6 characters.'}), 400
    try:
        with db() as con:
            cur = con.execute('INSERT INTO users(name,email,password) VALUES(?,?,?)',
                               (name,email.lower(),generate_password_hash(password)))
            session['user_id'] = cur.lastrowid
        return jsonify({'message':'Account created successfully.','user':current_user()}), 201
    except sqlite3.IntegrityError:
        return jsonify({'error':'An account with this email already exists.'}), 409

@app.post('/api/login')
def login():
    data = request.get_json(silent=True) or {}
    with db() as con:
        user = con.execute('SELECT * FROM users WHERE email=?', (str(data.get('email','')).lower().strip(),)).fetchone()
    if not user or not check_password_hash(user['password'], str(data.get('password',''))):
        return jsonify({'error':'Incorrect email or password.'}), 401
    session['user_id'] = user['id']
    return jsonify({'message':'Welcome back!','user':current_user()})

@app.post('/api/logout')
def logout():
    session.clear(); return jsonify({'message':'Logged out.'})

@app.get('/api/vehicles')
def vehicles():
    search = request.args.get('search','').strip()
    category = request.args.get('category','').strip()
    sql = 'SELECT * FROM vehicles WHERE available=1'
    args = []
    if search:
        sql += ' AND (name LIKE ? OR model LIKE ? OR location LIKE ?)'
        args += [f'%{search}%']*3
    if category and category != 'All': sql += ' AND category=?'; args.append(category)
    sql += ' ORDER BY id DESC'
    with db() as con: rows = con.execute(sql,args).fetchall()
    return jsonify({'vehicles':[dict(r) for r in rows]})

@app.post('/api/bookings')
@login_required
def create_booking():
    data = request.get_json(silent=True) or {}
    try:
        vehicle_id = int(data.get('vehicle_id'))
        start = datetime.strptime(data.get('start_date',''), '%Y-%m-%d').date()
        end = datetime.strptime(data.get('end_date',''), '%Y-%m-%d').date()
    except (ValueError, TypeError): return jsonify({'error':'Please select valid booking dates.'}), 400
    if end < start: return jsonify({'error':'End date must be on or after the start date.'}), 400
    days = (end-start).days + 1
    with db() as con:
        vehicle = con.execute('SELECT * FROM vehicles WHERE id=? AND available=1',(vehicle_id,)).fetchone()
        if not vehicle: return jsonify({'error':'This vehicle is not available.'}), 404
        conflict = con.execute('''SELECT id FROM bookings WHERE vehicle_id=? AND status='Confirmed'
            AND NOT (end_date < ? OR start_date > ?)''',(vehicle_id,start.isoformat(),end.isoformat())).fetchone()
        if conflict: return jsonify({'error':'This vehicle is already booked for those dates.'}), 409
        total = days * vehicle['price']
        cur = con.execute('INSERT INTO bookings(user_id,vehicle_id,start_date,end_date,total) VALUES(?,?,?,?,?)',
                          (session['user_id'],vehicle_id,start.isoformat(),end.isoformat(),total))
        con.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',
                    (session['user_id'],f"Your booking for {vehicle['name']} is confirmed."))
    return jsonify({'message':'Booking confirmed!','booking_id':cur.lastrowid,'total':total}), 201

@app.get('/api/bookings')
@login_required
def my_bookings():
    user = current_user()
    with db() as con:
        if user['role']=='admin':
            rows = con.execute('''SELECT b.*,v.name AS vehicle_name,u.name AS user_name,u.email FROM bookings b
                JOIN vehicles v ON v.id=b.vehicle_id JOIN users u ON u.id=b.user_id ORDER BY b.id DESC''').fetchall()
        else:
            rows = con.execute('''SELECT b.*,v.name AS vehicle_name FROM bookings b JOIN vehicles v ON v.id=b.vehicle_id
                WHERE b.user_id=? ORDER BY b.id DESC''',(user['id'],)).fetchall()
    return jsonify({'bookings':[dict(r) for r in rows]})

@app.get('/api/notifications')
@login_required
def notifications():
    with db() as con:
        rows=con.execute('SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC',(session['user_id'],)).fetchall()
    return jsonify({'notifications':[dict(r) for r in rows]})

@app.get('/api/admin/stats')
@admin_required
def admin_stats():
    with db() as con:
        return jsonify({
            'users':con.execute("SELECT COUNT(*) n FROM users WHERE role='user'").fetchone()['n'],
            'vehicles':con.execute('SELECT COUNT(*) n FROM vehicles').fetchone()['n'],
            'bookings':con.execute('SELECT COUNT(*) n FROM bookings').fetchone()['n'],
            'revenue':con.execute("SELECT COALESCE(SUM(total),0) n FROM bookings WHERE status='Confirmed'").fetchone()['n']
        })

@app.post('/api/admin/vehicles')
@admin_required
def add_vehicle():
    d=request.get_json(silent=True) or {}
    try:
        name=str(d.get('name','')).strip(); category=str(d.get('category','')).strip()
        model=str(d.get('model','')).strip(); location=str(d.get('location','')).strip(); price=float(d.get('price',0))
        if not all([name,category,model,location]) or price<=0: raise ValueError()
    except (ValueError,TypeError): return jsonify({'error':'Fill all vehicle fields and enter a valid price.'}),400
    with db() as con:
        cur=con.execute('INSERT INTO vehicles(name,category,model,price,location,description,image) VALUES(?,?,?,?,?,?,?)',
                        (name,category,model,price,location,str(d.get('description','')),str(d.get('image','')) or '🚘'))
    return jsonify({'message':'Vehicle added.','id':cur.lastrowid}),201

@app.delete('/api/admin/vehicles/<int:vehicle_id>')
@admin_required
def delete_vehicle(vehicle_id):
    with db() as con:
        con.execute('UPDATE vehicles SET available=0 WHERE id=?',(vehicle_id,))
    return jsonify({'message':'Vehicle removed from listings.'})

@app.post('/api/admin/bookings/<int:booking_id>/cancel')
@admin_required
def cancel_booking(booking_id):
    with db() as con:
        row=con.execute('SELECT user_id,vehicle_id FROM bookings WHERE id=?',(booking_id,)).fetchone()
        if not row: return jsonify({'error':'Booking not found.'}),404
        con.execute("UPDATE bookings SET status='Cancelled' WHERE id=?",(booking_id,))
        con.execute('INSERT INTO notifications(user_id,message) VALUES(?,?)',(row['user_id'],f'Booking #{booking_id} was cancelled by the administrator.'))
    return jsonify({'message':'Booking cancelled.'})

init_db()
if __name__ == '__main__':
    app.run(debug=True, port=5000)
