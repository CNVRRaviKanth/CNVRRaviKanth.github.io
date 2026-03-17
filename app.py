from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import random
import string

import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
# Use absolute path for database
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hotel_management.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

print(f"DATABASE PATH: {app.config['SQLALCHEMY_DATABASE_URI']}")

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    wallet_balance = db.Column(db.Float, default=0.0)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    price_per_night = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(120), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='confirmed') # 'confirmed', 'cancelled', 'rescheduled'

    room = db.relationship('Room', backref=db.backref('bookings', lazy=True))
    user = db.relationship('User', backref=db.backref('bookings', lazy=True))

@app.route('/')
def index():
    return render_template('landing.html')

@app.route('/rooms')
def rooms():
    all_rooms = Room.query.all()
    return render_template('index.html', rooms=all_rooms)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        logout_user() # Logout if someone is already logged in to prevent session mixup
        
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_exists = User.query.filter_by(email=email).first()
        if user_exists:
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logout_user() # Force logout to ensure clean session
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            
            # Check if there's a next page (from @login_required)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('rooms'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/topup', methods=['GET', 'POST'])
@login_required
def topup():
    if request.method == 'POST':
        amount = request.form.get('amount')
        try:
            amount = float(amount)
            if amount <= 0:
                flash('Please enter a valid amount.', 'danger')
                return redirect(url_for('topup'))
            
            current_user.wallet_balance += amount
            db.session.commit()
            flash(f'Successfully topped up ${amount:.2f}!', 'success')
            return redirect(url_for('rooms'))
        except ValueError:
            flash('Invalid amount entered.', 'danger')
            return redirect(url_for('topup'))
            
    return render_template('topup.html')

@app.route('/book/<int:room_id>')
@login_required
def book(room_id):
    room = Room.query.get_or_404(room_id)
    return render_template('book.html', room=room)

@app.route('/submit', methods=['POST'])
@login_required
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

        if current_user.wallet_balance < total_price:
            flash(f'Insufficient funds! Your balance is ${current_user.wallet_balance:.2f}, but the total is ${total_price:.2f}. Please top up.', 'danger')
            return redirect(url_for('topup'))

        # Deduct balance
        current_user.wallet_balance -= total_price

        new_booking = Booking(
            user_id=current_user.id,
            room_id=room_id,
            guest_name=guest_name,
            guest_email=guest_email,
            check_in_date=check_in,
            check_out_date=check_out,
            total_price=total_price
        )
        db.session.add(new_booking)
        db.session.commit()
        
        flash(f'Booking successful! ${total_price:.2f} deducted from your wallet.', 'success')
        return redirect(url_for('my_bookings'))

@app.route('/cancel-booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('my_bookings'))
    
    if booking.status == 'cancelled':
        flash('Booking is already cancelled.', 'warning')
        return redirect(url_for('my_bookings'))
    
    # Penalty calculation (10%)
    penalty = booking.total_price * 0.1
    refund_amount = booking.total_price - penalty
    
    current_user.wallet_balance += refund_amount
    booking.status = 'cancelled'
    db.session.commit()
    
    flash(f'Booking cancelled. 10% penalty (${penalty:.2f}) applied. ${refund_amount:.2f} refunded to your wallet.', 'success')
    return redirect(url_for('my_bookings'))

@app.route('/reschedule/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def reschedule_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('my_bookings'))
    
    if booking.status == 'cancelled':
        flash('Cannot reschedule a cancelled booking.', 'danger')
        return redirect(url_for('my_bookings'))
        
    if request.method == 'POST':
        new_check_in_str = request.form['check_in_date']
        new_check_out_str = request.form['check_out_date']
        
        new_check_in = datetime.strptime(new_check_in_str, '%Y-%m-%d').date()
        new_check_out = datetime.strptime(new_check_out_str, '%Y-%m-%d').date()
        
        days = (new_check_out - new_check_in).days
        if days <= 0:
            flash('Check-out date must be after check-in date!', 'danger')
            return redirect(url_for('reschedule_booking', booking_id=booking_id))
            
        # Reschedule penalty (5% of original price)
        penalty = booking.total_price * 0.05
        
        if current_user.wallet_balance < penalty:
            flash(f'Insufficient funds for rescheduling penalty (${penalty:.2f}). Please top up.', 'danger')
            return redirect(url_for('topup'))
            
        # Update dates and deduct penalty
        current_user.wallet_balance -= penalty
        booking.check_in_date = new_check_in
        booking.check_out_date = new_check_out
        booking.status = 'rescheduled'
        # Recalculate total price if stay duration changed
        new_total_price = days * booking.room.price_per_night
        booking.total_price = new_total_price
        
        db.session.commit()
        
        flash(f'Booking rescheduled. 5% penalty (${penalty:.2f}) deducted. New total: ${new_total_price:.2f}', 'success')
        return redirect(url_for('my_bookings'))
        
    return render_template('reschedule.html', booking=booking)
        
@app.route('/my-bookings')
@login_required
def my_bookings():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.check_in_date.desc()).all()
    return render_template('my_bookings.html', bookings=user_bookings)

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