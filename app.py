from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from datetime import datetime
import random
import string
import os
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'hotel_management.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    wallet_balance = db.Column(db.Float, default=0.0)
    is_admin = db.Column(db.Boolean, default=False)

    @property
    def has_active_booking(self):
        return any(b.status in ['confirmed', 'rescheduled'] for b in self.bookings)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    category = db.Column(db.String(50), nullable=False, default='Business')
    price_per_night = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    capacity = db.Column(db.String(50), nullable=False, default='Single')
    max_capacity = db.Column(db.Integer, default=1)
    total_rooms = db.Column(db.Integer, default=10)
    available_rooms = db.Column(db.Integer, default=10)

class ExtraService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)

class FoodItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False) # Tiffin, Drink
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)

class TourismPackage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    duration = db.Column(db.String(50), nullable=False)

booking_services = db.Table('booking_services',
    db.Column('booking_id', db.Integer, db.ForeignKey('booking.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('extra_service.id'), primary_key=True)
)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    guest_name = db.Column(db.String(100), nullable=False)
    guest_email = db.Column(db.String(120), nullable=False)
    check_in_date = db.Column(db.Date, nullable=False)
    check_out_date = db.Column(db.Date, nullable=False)
    total_price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='confirmed')
    service_cost = db.Column(db.Float, default=0.0)

    room = db.relationship('Room', backref=db.backref('bookings', lazy=True))
    user = db.relationship('User', backref=db.backref('bookings', lazy=True, cascade='all, delete-orphan'))
    services = db.relationship('ExtraService', secondary=booking_services, backref=db.backref('bookings', lazy='dynamic'))

class TourismBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('tourism_package.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='confirmed')

    package = db.relationship('TourismPackage', backref=db.backref('bookings', lazy=True))
    user = db.relationship('User', backref=db.backref('tourism_bookings', lazy=True, cascade='all, delete-orphan'))

class FoodOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey('food_item.id'), nullable=False)
    price = db.Column(db.Float, nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)

    food = db.relationship('FoodItem', backref=db.backref('orders', lazy=True))
    user = db.relationship('User', backref=db.backref('food_orders', lazy=True, cascade='all, delete-orphan'))

class BookingGuest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    aadhar_number = db.Column(db.String(12), nullable=False)

    booking = db.relationship('Booking', backref=db.backref('guests', lazy=True, cascade='all, delete-orphan'))

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
        logout_user()
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        # Password complexity validation
        import re
        password_pattern = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
        if not re.match(password_pattern, password):
            flash('Password must be at least 8 characters long and include: one uppercase, one lowercase, one number, and one special character.', 'danger')
            return redirect(url_for('register'))

        user_exists = User.query.filter_by(username=username).first()
        if user_exists:
            flash('Username already registered', 'danger')
            return redirect(url_for('register'))
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(username=username, email=email, password_hash=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        logout_user()
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('rooms'))
        else:
            flash('Login Unsuccessful.', 'danger')
    return render_template('login.html')

@app.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    try:
        user_id = current_user.id
        user = User.query.get(user_id)
        if user:
            logout_user()
            db.session.delete(user)
            db.session.commit()
            flash('Your account and all associated data have been permanently deleted.', 'success')
        else:
            flash('User not found.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting account: {str(e)}', 'danger')
    return redirect(url_for('index'))

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
                flash('Invalid amount.', 'danger')
                return redirect(url_for('topup'))
            current_user.wallet_balance += amount
            db.session.commit()
            flash(f'Topped up ₹{amount:.2f}!', 'success')
            return redirect(url_for('rooms'))
        except ValueError:
            flash('Invalid amount.', 'danger')
    return render_template('topup.html')

@app.route('/book/<int:room_id>')
@login_required
def book(room_id):
    room = Room.query.get_or_404(room_id)
    if room.available_rooms <= 0:
        flash('Room fully booked.', 'warning')
        return redirect(url_for('rooms'))
    services = ExtraService.query.all()
    return render_template('book.html', room=room, services=services)

@app.route('/submit', methods=['POST'])
@login_required
def submit():
    room_id = request.form['room_id']
    guest_name = request.form['guest_name']
    guest_email = request.form['guest_email']
    check_in_str = request.form['check_in_date']
    check_out_str = request.form['check_out_date']
    selected_service_ids = request.form.getlist('services')
    
    check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
    check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()
    days = (check_out - check_in).days
    
    if days <= 0:
        flash('Check-out must be after check-in!', 'danger')
        return redirect(url_for('book', room_id=room_id))
        
    room = Room.query.get(room_id)
    if room.available_rooms <= 0:
        flash('Room no longer available.', 'danger')
        return redirect(url_for('rooms'))

    room_price = days * room.price_per_night
    service_cost = 0.0
    selected_services = []
    for s_id in selected_service_ids:
        service = ExtraService.query.get(int(s_id))
        if service:
            service_cost += service.price
            selected_services.append(service)
    
    total_price = room_price + service_cost
    if current_user.wallet_balance < total_price:
        flash(f'Insufficient funds for booking! Total: ₹{total_price:.2f}.', 'danger')
        return redirect(url_for('topup'))

    current_user.wallet_balance -= total_price
    room.available_rooms -= 1

    new_booking = Booking(
        user_id=current_user.id, room_id=room_id, guest_name=guest_name,
        guest_email=guest_email, check_in_date=check_in, check_out_date=check_out,
        total_price=total_price, service_cost=service_cost
    )
    new_booking.services.extend(selected_services)
    
    # Add guests
    guest_names = request.form.getlist('extra_name')
    guest_emails = request.form.getlist('extra_email')
    guest_aadhars = request.form.getlist('extra_aadhar')
    primary_aadhar = request.form.get('guest_aadhar')

    # Validate Aadhar lengths
    if not (primary_aadhar and len(primary_aadhar) == 12 and primary_aadhar.isdigit()):
        flash('Primary guest Aadhar must be exactly 12 digits.', 'danger')
        return redirect(url_for('book', room_id=room_id))
    
    # Add primary guest to guest list table as well for consistency
    primary_guest_entry = BookingGuest(booking=new_booking, name=guest_name, email=guest_email, aadhar_number=primary_aadhar)
    db.session.add(primary_guest_entry)

    for i in range(len(guest_names)):
        if guest_names[i] and guest_emails[i] and guest_aadhars[i]:
            if not (len(guest_aadhars[i]) == 12 and guest_aadhars[i].isdigit()):
                flash(f'Guest {i+2} Aadhar must be exactly 12 digits.', 'danger')
                return redirect(url_for('book', room_id=room_id))
            extra_guest = BookingGuest(booking=new_booking, name=guest_names[i], email=guest_emails[i], aadhar_number=guest_aadhars[i])
            db.session.add(extra_guest)

    db.session.add(new_booking)
    db.session.commit()
    
    flash(f'Booking successful! Total: ₹{total_price:.2f}.', 'success')
    return redirect(url_for('my_bookings'))

@app.route('/food')
@login_required
def food_menu():
    if not current_user.has_active_booking:
        flash('Food menu is only available for guests with active bookings.', 'warning')
        return redirect(url_for('rooms'))
    tiffins = FoodItem.query.filter_by(category='Tiffin').all()
    drinks = FoodItem.query.filter_by(category='Drink').all()
    return render_template('food.html', tiffins=tiffins, drinks=drinks)

@app.route('/order-food/<int:food_id>')
@login_required
def order_food(food_id):
    food = FoodItem.query.get_or_404(food_id)
    if not current_user.has_active_booking:
        flash('You must have a booking to order food.', 'warning')
        return redirect(url_for('rooms'))
    if current_user.wallet_balance < food.price:
        flash(f'Insufficient funds for {food.name}!', 'danger')
        return redirect(url_for('topup'))
    
    current_user.wallet_balance -= food.price
    new_order = FoodOrder(user_id=current_user.id, food_id=food.id, price=food.price)
    db.session.add(new_order)
    db.session.commit()
    flash(f'Ordered {food.name}! ₹{food.price:.2f} deducted.', 'success')
    return redirect(url_for('food_menu'))

@app.route('/tourism')
def tourism():
    packages = TourismPackage.query.all()
    return render_template('tourism.html', packages=packages)

@app.route('/buy-package/<int:package_id>')
@login_required
def buy_package(package_id):
    package = TourismPackage.query.get_or_404(package_id)
    if current_user.wallet_balance < package.price:
        flash(f'Insufficient funds for {package.name}!', 'danger')
        return redirect(url_for('topup'))
    
    current_user.wallet_balance -= package.price
    new_tourism_booking = TourismBooking(user_id=current_user.id, package_id=package.id, price=package.price, status='confirmed')
    db.session.add(new_tourism_booking)
    db.session.commit()
    flash(f'Successfully booked {package.name}! ₹{package.price:.2f} deducted.', 'success')
    return redirect(url_for('my_bookings'))

@app.route('/cancel-booking/<int:booking_id>')
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('my_bookings'))
    if booking.status == 'cancelled':
        flash('Already cancelled.', 'warning')
        return redirect(url_for('my_bookings'))
    
    penalty = booking.total_price * 0.1
    refund_amount = booking.total_price - penalty
    current_user.wallet_balance += refund_amount
    booking.status = 'cancelled'
    booking.room.available_rooms += 1
    db.session.commit()
    flash(f'Cancelled. ₹{refund_amount:.2f} refunded.', 'success')
    return redirect(url_for('my_bookings'))

@app.route('/reschedule-tourism/<int:booking_id>', methods=['GET', 'POST'])
@login_required
def reschedule_tourism_booking(booking_id):
    booking = TourismBooking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('my_bookings'))
    if booking.status == 'cancelled':
        flash('Cannot reschedule a cancelled booking.', 'danger')
        return redirect(url_for('my_bookings'))
    
    if request.method == 'POST':
        new_date_str = request.form['booking_date']
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()
        
        penalty = booking.price * 0.05
        if current_user.wallet_balance < penalty:
            flash(f'Insufficient funds for penalty (₹{penalty:.2f}).', 'danger')
            return redirect(url_for('topup'))
            
        current_user.wallet_balance -= penalty
        booking.booking_date = new_date
        booking.status = 'rescheduled'
        db.session.commit()
        
        flash(f'Tourism plan rescheduled! ₹{penalty:.2f} penalty deducted.', 'success')
        return redirect(url_for('my_bookings'))
        
    return render_template('reschedule_tourism.html', booking=booking)

@app.route('/cancel-tourism/<int:booking_id>')
@login_required
def cancel_tourism_booking(booking_id):
    booking = TourismBooking.query.get_or_404(booking_id)
    if booking.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('my_bookings'))
    if booking.status == 'cancelled':
        flash('Already cancelled.', 'warning')
        return redirect(url_for('my_bookings'))
    
    penalty = booking.price * 0.1
    refund_amount = booking.price - penalty
    current_user.wallet_balance += refund_amount
    booking.status = 'cancelled'
    db.session.commit()
    flash(f'Tourism booking cancelled. ₹{refund_amount:.2f} refunded.', 'success')
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
            flash('Check-out must be after check-in!', 'danger')
            return redirect(url_for('reschedule_booking', booking_id=booking_id))
        penalty = booking.total_price * 0.05
        if current_user.wallet_balance < penalty:
            flash(f'Insufficient funds for penalty (${penalty:.2f}).', 'danger')
            return redirect(url_for('topup'))
        current_user.wallet_balance -= penalty
        booking.check_in_date = new_check_in
        booking.check_out_date = new_check_out
        booking.status = 'rescheduled'
        booking.total_price = days * booking.room.price_per_night
        db.session.commit()
        flash(f'Rescheduled! ${penalty:.2f} penalty deducted.', 'success')
        return redirect(url_for('my_bookings'))
    return render_template('reschedule.html', booking=booking)

@app.route('/my-bookings')
@login_required
def my_bookings():
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.check_in_date.desc()).all()
    tourism_bookings = TourismBooking.query.filter_by(user_id=current_user.id).order_by(TourismBooking.booking_date.desc()).all()
    food_orders = FoodOrder.query.filter_by(user_id=current_user.id).order_by(FoodOrder.order_date.desc()).all()
    return render_template('my_bookings.html', bookings=user_bookings, tourism_bookings=tourism_bookings, food_orders=food_orders)

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    rooms = Room.query.all()
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    services = ExtraService.query.all()
    return render_template('admin_dashboard.html', rooms=rooms, bookings=bookings, services=services)

@app.route('/admin/add-room', methods=['GET', 'POST'])
@login_required
@admin_required
def add_room():
    if request.method == 'POST':
        name = request.form.get('name')
        rtype = request.form.get('type')
        price = float(request.form.get('price'))
        desc = request.form.get('description')
        capacity = request.form.get('capacity')
        category = request.form.get('category')
        total = int(request.form.get('total_rooms'))
        new_room = Room(name=name, type=rtype, category=category, price_per_night=price, description=desc, capacity=capacity, total_rooms=total, available_rooms=total)
        db.session.add(new_room)
        db.session.commit()
        flash('Room added!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_room_form.html', title='Add Room')

@app.route('/admin/edit-room/<int:room_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_room(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.name = request.form.get('name')
        room.type = request.form.get('type')
        room.price_per_night = float(request.form.get('price'))
        room.description = request.form.get('description')
        room.capacity = request.form.get('capacity')
        room.category = request.form.get('category')
        old_total = room.total_rooms
        new_total = int(request.form.get('total_rooms'))
        room.available_rooms += (new_total - old_total)
        room.total_rooms = new_total
        db.session.commit()
        flash('Room updated!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('admin_room_form.html', title='Edit Room', room=room)

@app.route('/success')
def success():
    return render_template('success.html')

if __name__ == '__main__':
    with app.app_context():
        # Using create_all() to ensure schema exists. 
        # WARNING: For production, use Flask-Migrate instead.
        db.create_all()
        
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            hashed_pw = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(username='admin', email='admin@hotel.com', password_hash=hashed_pw, is_admin=True, wallet_balance=50000.0)
            db.session.add(admin)
        else:
            # Re-hash for verification during debugging
            admin.password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
            
        if not Room.query.first():
            # Travel Category (Budget)
            db.session.add(Room(name='Compact Solo', type='Single', category='Travel', price_per_night=1500.0, description='Perfect for solo travelers on a budget.', capacity='Single', max_capacity=1, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Traveler’s Twin', type='Double', category='Travel', price_per_night=2200.0, description='Standard twin room for budget explorers.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Backpacker’s Dorm', type='Shared', category='Travel', price_per_night=1800.0, description='Social atmosphere for global nomads.', capacity='Shared', max_capacity=4, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Standard Double', type='Double', category='Travel', price_per_night=2800.0, description='Classic comfort at an affordable price.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Explorer Suite', type='Suite', category='Travel', price_per_night=3500.0, description='A bit of extra space for your travel gear.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))

            # Family Category
            db.session.add(Room(name='Family Standard', type='Shared', category='Family', price_per_night=4500.0, description='Comfortable stay for small families.', capacity='Three Shared', max_capacity=3, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Bunk Bed Paradise', type='Shared', category='Family', price_per_night=5200.0, description='Fun room design for families with kids.', capacity='Four Shared', max_capacity=4, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Connected Suite', type='Suite', category='Family', price_per_night=7500.0, description='Two interconnected rooms for privacy and family time.', capacity='Four Shared', max_capacity=4, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Grand Family Suite', type='Suite', category='Family', price_per_night=9500.0, description='Luxury and space for the whole family.', capacity='Four Shared', max_capacity=4, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Family Cottage Room', type='Shared', category='Family', price_per_night=6000.0, description='Cozy cottage-style room for a homely feel.', capacity='Three Shared', max_capacity=3, total_rooms=10, available_rooms=10))

            # Business Category
            db.session.add(Room(name='Executive Solo', type='Single', category='Business', price_per_night=5500.0, description='Efficient workspace and premium comfort.', capacity='Single', max_capacity=1, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Corporate Double', type='Double', category='Business', price_per_night=7000.0, description='Ideal for corporate partners or colleagues.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Business Suite', type='Suite', category='Business', price_per_night=12000.0, description='Luxury amenities for the modern professional.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Meeting-Ready Suite', type='Suite', category='Business', price_per_night=15000.0, description='Includes a small meeting area for your convenience.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Work-From-Suite', type='Suite', category='Business', price_per_night=8500.0, description='A perfect blend of work and relaxation.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))

            # Luxury Category
            db.session.add(Room(name='Royal Suite', type='Suite', category='Luxury', price_per_night=18000.0, description='Live like royalty in our most popular luxury suite.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Presidential Suite', type='Suite', category='Luxury', price_per_night=35000.0, description='Unparalleled luxury with exclusive services.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Penthouse View', type='Suite', category='Luxury', price_per_night=45000.0, description='Stunning city views from our top-floor suite.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))
            db.session.add(Room(name='Luxury Penthouse', type='Suite', category='Luxury', price_per_night=55000.0, description='The pinnacle of hotel luxury and comfort.', capacity='Two Shared', max_capacity=2, total_rooms=10, available_rooms=10))

        if not ExtraService.query.first():
            db.session.add(ExtraService(name='Breakfast Buffet', price=450.0))
            db.session.add(ExtraService(name='Express Laundry', price=300.0))
            db.session.add(ExtraService(name='Airport Transfer', price=1200.0))
            db.session.add(ExtraService(name='Late Check-out', price=800.0))

        if not FoodItem.query.first():
            # Tiffins
            db.session.add(FoodItem(name='Butter Masala Dosa', category='Tiffin', price=180.0, description='Crispy crepe with spiced potato filling and chutney.'))
            db.session.add(FoodItem(name='Idli Sambar (3 pcs)', category='Tiffin', price=120.0, description='Soft steamed rice cakes served with authentic sambar.'))
            db.session.add(FoodItem(name='Indore Poha', category='Tiffin', price=80.0, description='Flattened rice with onions, peas, sev and lemon.'))
            db.session.add(FoodItem(name='Paneer Paratha', category='Tiffin', price=150.0, description='Whole wheat flatbread stuffed with spiced paneer.'))
            
            # Drinks
            db.session.add(FoodItem(name='Masala Chai', category='Drink', price=40.0, description='Traditional Indian ginger-cardamom tea.'))
            db.session.add(FoodItem(name='Mango Lassi', category='Drink', price=90.0, description='Refreshing yogurt-based thick mango drink.'))
            db.session.add(FoodItem(name='Cold Coffee', category='Drink', price=120.0, description='Creamy iced coffee topped with chocolate powder.'))
            db.session.add(FoodItem(name='Fresh Lime Soda', category='Drink', price=70.0, description='Refreshing sweet and salty lime soda.'))

        if not TourismPackage.query.first():
            db.session.add(TourismPackage(name='Heritage City Tour', price=2500.0, description='Visit historical monuments and museums with a guide.', duration='6 Hours'))
            db.session.add(TourismPackage(name='Sacred Temple Visit', price=1500.0, description='Spiritual journey to the most famous city temples.', duration='4 Hours'))
            db.session.add(TourismPackage(name='Nature Hill Trek', price=3500.0, description='Guided trekking experience with breakfast and kit.', duration='Full Day'))
            db.session.add(TourismPackage(name='Night Market Walk', price=800.0, description='Explore local street food and shopping hotspots.', duration='3 Hours'))

        db.session.commit()
    app.run(debug=True, port=5001)

## pkill -f "python hotel_management/app.py" || true