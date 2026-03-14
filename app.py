from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Models
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(120), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)

    room = db.relationship('Room', backref=db.backref('bookings', lazy=True))

@app.route('/')
def index():
    rooms = Room.query.all()
    return render_template('index.html', rooms=rooms)

@app.route('/book/<int:room_id>')
def book(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template('book.html', room=room)

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        room_id = request.form['room_id']
        guest_name = request.form['guest_name']
        guest_email = request.form['guest_email']
        check_in_str = request.form['check_in_date']
        check_out_str = request.form['check_out_date']
        
        # Calculate days and price
        check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
        check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
        days = (check_out - check_in).days
        
        if days <= 0:
            flash('Check-out date must be after check-in date!', 'danger')
            return redirect(url_for('book', room_id=room_id))
            
        room = Room.query.get(room_id)
        total_price = days * room.price_per_night

        new_booking = Booking(
            room_id=room_id,
            guest_name=guest_name,
            guest_email=guest_email,
            check_in_date=check_in,
            check_out_date=check_out,
            total_price=total_price
        )
        db.session.add(new_booking)
        db.session.commit()
        
        return redirect(url_for('success'))
        
@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Add dummy data if rooms are empty
        if not Room.query.first():
            db.session.add(Room(name='Standard Room', type='Single', price_per_night=50, description='A cozy single room.'))
            db.session.add(Room(name='Deluxe Suite', type='Suite', price_per_night=150, description='A luxurious suite with a great view.'))
            db.session.commit()
    app.run(debug=True)
