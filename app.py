from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from extensions import db  # ✅ main db instance
from models import User, Referrals, Withdrawals, PendingUsers, InviteLog, TopInviterTracker, Announcement  
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.secret_key = 'G0D_super_001_key'

# Setup DB path
basedir = os.path.abspath(os.path.dirname(__file__))

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ✅ Initialize the db with the app
db.init_app(app)

# ✅ Create tables automatically (if they don't exist yet)
with app.app_context():
    db.create_all()

# Home route
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/instructions')
def instructions():
    return render_template('instructions.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        # Check if username already exists in approved or pending users
        if User.query.filter_by(username=username).first() or PendingUsers.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('signup'))

        now = datetime.now()

        # Create a pending user entry
        new_pending_user = PendingUsers(
            username=username,
            email=email,
            phone=phone,
            password=password,
            date=now.strftime('%Y-%m-%d'),
            time=now.strftime('%H:%M:%S'),
            status='pending'
        )
        db.session.add(new_pending_user)

        # Handle referral logic
        inviter = session.get('inviter')
        if inviter and inviter != username:
            # Save to Referrals Table (for rewards)
            referral = Referrals(
                inviter_username=inviter,
                invitee_username=username,
                profit=50
            )
            db.session.add(referral)

            # ✅ Save to InviteLog (used by rewards system)
            invite_log = InviteLog(
                inviter_username=inviter,
                timestamp=datetime.utcnow()
            )
            db.session.add(invite_log)

        db.session.commit()

        # Clear inviter session after signup
        session.pop('inviter', None)

        flash('Signup request submitted! Await admin approval.', 'success')
        return redirect(url_for('instruction'))

    # Render signup form and show inviter if present
    return render_template('signup.html', inviter=session.get('inviter'))


@app.route('/instruction')
def instruction():
    if 'username' not in session:
        return redirect(url_for('login'))  # Ensure only logged-in users can view this if needed
    return render_template('instruction.html')


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            session['role'] = user.role

            flash(f"Successfully logged in as {user.username}", "success")

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('dashboard'))

        flash('Invalid username or password', 'error')
        return redirect(url_for('login'))

    return render_template('login.html')



@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')

    current_user = User.query.filter_by(username=session['username']).first()

    if not current_user:
        flash("User not found.")
        return redirect('/login')

    # Count approved invitees
    invitees_count = Referrals.query.filter_by(inviter_username=current_user.username).count()

    # Calculate profits (KES 50 per approved invitee)
    profits = invitees_count * 50

    # Total amount withdrawn (only approved withdrawals)
    approved_withdrawals = Withdrawals.query.filter_by(username=current_user.username, status='approved').all()
    total_withdrawn = sum(w.amount for w in approved_withdrawals)

    # Final balance = profits - approved withdrawals
    balance = profits - total_withdrawn

    # ✅ Dynamically update user's record
    current_user.invitees = invitees_count
    current_user.profits = profits
    current_user.balance = balance
    db.session.commit()

    # Unique invite link
    invite_link = f"{request.host_url}invite/{current_user.username}"

    return render_template('dashboard.html',
                           username=current_user.username,
                           invitees=invitees_count,
                           profits=profits,
                           balance=balance,
                           invite_link=invite_link)


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    return render_template('admin_dashboard.html')


@app.route('/withdraw', methods=['GET', 'POST'])
def withdraw():
    if 'username' not in session:
        return redirect(url_for('login'))

    current_user = User.query.filter_by(username=session['username']).first()

    if not current_user:
        flash('User not found.', 'error')
        return redirect(url_for('login'))

    # Real-time referral profit calculation
    invitees_count = Referrals.query.filter_by(inviter_username=current_user.username).count()
    profits = invitees_count * 50

    # Real-time total withdrawn
    approved_withdrawals = Withdrawals.query.filter_by(username=current_user.username, status='approved').all()
    total_withdrawn = sum(w.amount for w in approved_withdrawals)

    # Final real-time balance
    real_balance = profits - total_withdrawn

    # Update user record in database
    current_user.profits = profits
    current_user.invitees = invitees_count
    current_user.balance = real_balance
    db.session.commit()

    if request.method == 'POST':
        phone = request.form['phone']
        amount = int(request.form['amount'])

        if amount < 150:
            flash('Minimum withdrawal amount is Ksh 150', 'error')
            return redirect(url_for('withdraw'))

        if real_balance < amount:
            flash('Insufficient balance.', 'error')
            return redirect(url_for('withdraw'))

        now = datetime.now()
        new_withdrawal = Withdrawals(
            username=current_user.username,
            date=now.strftime('%Y-%m-%d'),
            time=now.strftime('%H:%M:%S'),
            amount=amount,
            phone=phone,
            balance=real_balance,  # snapshot at time of request
            status='pending'
        )
        db.session.add(new_withdrawal)
        db.session.commit()

        flash('Withdrawal request submitted successfully.', 'success')
        return redirect(url_for('withdraw'))

    # Withdrawal history
    history = Withdrawals.query.filter_by(username=current_user.username).order_by(Withdrawals.id.desc()).all()

    return render_template('withdraw.html', withdrawals=history)


@app.route('/admin/withdrawals')
def admin_withdrawals():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    withdrawals = Withdrawals.query.order_by(Withdrawals.date.desc(), Withdrawals.time.desc()).all()
    return render_template('admin_withdrawals.html', withdrawals=withdrawals)


@app.route('/admin/withdrawals/approve/<int:withdrawal_id>')
def approve_withdrawal(withdrawal_id):
    withdrawal = Withdrawals.query.get_or_404(withdrawal_id)

    if withdrawal.status != 'pending':
        flash('This withdrawal has already been processed.', 'warning')
        return redirect(url_for('admin_withdrawals'))

    user = User.query.filter_by(username=withdrawal.username).first()

    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_withdrawals'))

    if user.balance is None or user.balance < withdrawal.amount:
        flash('Insufficient user balance to approve this withdrawal.', 'danger')
        return redirect(url_for('admin_withdrawals'))

    # Approve and deduct
    user.balance -= withdrawal.amount
    withdrawal.status = 'approved'
    db.session.commit()
    flash(f'Withdrawal ID {withdrawal.id} approved and balance updated.', 'success')
    return redirect(url_for('admin_withdrawals'))


@app.route('/admin/withdrawals/deny/<int:withdrawal_id>')
def deny_withdrawal(withdrawal_id):
    withdrawal = Withdrawals.query.get_or_404(withdrawal_id)

    if withdrawal.status != 'pending':
        flash('This withdrawal has already been processed.', 'warning')
        return redirect(url_for('admin_withdrawals'))

    withdrawal.status = 'denied'
    db.session.commit()
    flash(f'Withdrawal ID {withdrawal.id} denied.', 'warning')
    return redirect(url_for('admin_withdrawals'))

@app.route('/invite/<inviter_username>')
def invite(inviter_username):
    session['inviter'] = inviter_username  # store who invited the user
    return redirect(url_for('signup'))  # redirect to signup page

@app.route('/admin_user_requests')
def admin_user_requests():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    requests = PendingUsers.query.order_by(PendingUsers.id.desc()).all()
    return render_template('admin_user_requests.html', requests=requests)

@app.route('/approve_user/<int:user_id>')
def approve_user(user_id):
    request = db.session.get(PendingUsers, user_id)
    if request:
        new_user = User(username=request.username, email=request.email, password=request.password)
        db.session.add(new_user)
        db.session.delete(request)
        db.session.commit()
        flash(f"{request.username} has been approved.", 'success')
    return redirect(url_for('admin_user_requests'))

@app.route('/deny_user/<int:user_id>')
def deny_user(user_id):
    request = db.session.get(PendingUsers, user_id)
    if request:
        request.status = 'denied'
        db.session.commit()
        flash(f"{request.username} has been denied.", 'error')
    return redirect(url_for('admin_user_requests'))

@app.route('/rewards')
def rewards():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    yesterday_end = today_start - timedelta(microseconds=1)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    year_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    def count_user_invites(start_time):
        return InviteLog.query.filter(
            InviteLog.inviter_username == username,
            InviteLog.timestamp >= start_time
        ).count()

    my_invites = {
        'today': count_user_invites(today_start),
        'week': count_user_invites(week_start),
        'month': count_user_invites(month_start),
        'year': count_user_invites(year_start)
    }

    def get_top_inviters(start_time):
        return db.session.query(
            InviteLog.inviter_username,
            db.func.count(InviteLog.id).label("invite_count")
        ).filter(
            InviteLog.timestamp >= start_time
        ).group_by(
            InviteLog.inviter_username
        ).order_by(
            db.desc("invite_count")
        ).limit(3).all()

    top_inviter_tracker = {
        'day': get_top_inviters(today_start),
        'week': get_top_inviters(week_start),
        'month': get_top_inviters(month_start),
        'year': get_top_inviters(year_start),
    }

    # Get or create tracker record
    tracker = TopInviterTracker.query.filter_by(username=username).first()
    if not tracker:
        tracker = TopInviterTracker(username=username, crown_count=0)
        db.session.add(tracker)
        db.session.commit()

    # ✅ Crown Award Function
    def award_crowns_if_top():
        # Check yesterday's top inviter
        top_yesterday = db.session.query(
            InviteLog.inviter_username,
            db.func.count(InviteLog.id).label("invite_count")
        ).filter(
            InviteLog.timestamp >= yesterday_start,
            InviteLog.timestamp <= yesterday_end
        ).group_by(
            InviteLog.inviter_username
        ).order_by(
            db.desc("invite_count")
        ).first()

        if top_yesterday and top_yesterday.inviter_username == username:
            if not tracker.last_awarded or tracker.last_awarded.date() < now.date():
                tracker.crown_count += 1

                # Reset if reached 3
                if tracker.crown_count >= 3:
                    tracker.crown_count = 0

                tracker.last_awarded = now
                db.session.commit()

    # ✅ Call crown check
    award_crowns_if_top()

    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).all()

    return render_template(
        "rewards.html",
        username=username,
        my_invites=my_invites,
        crown_count=tracker.crown_count,
        announcements=announcements,
        top_inviter_tracker=top_inviter_tracker,
        user_crowns=tracker.crown_count
    )

# AJAX Endpoint: Live stats and leaderboards
@app.route('/rewards/data')
def rewards_data():
    username = session.get('username')
    if not username:
        return jsonify({"error": "User not logged in"}), 401

    now = datetime.utcnow()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    start_of_year = today.replace(month=1, day=1)

    def get_top(start_time):
        results = db.session.query(
            InviteLog.inviter_username,
            db.func.count(InviteLog.id).label("invite_count")
        ).filter(
            InviteLog.timestamp >= start_time
        ).group_by(
            InviteLog.inviter_username
        ).order_by(
            db.desc("invite_count")
        ).limit(3).all()

        return [{"username": r.inviter_username, "invite_count": r.invite_count} for r in results]

    def count_user(start_time):
        return InviteLog.query.filter(
            InviteLog.inviter_username == username,
            InviteLog.timestamp >= start_time
        ).count()

    return jsonify({
        "top_day": get_top(today),
        "top_week": get_top(start_of_week),
        "top_month": get_top(start_of_month),
        "top_year": get_top(start_of_year),
        "my_today": count_user(today),
        "my_week": count_user(start_of_week),
        "my_month": count_user(start_of_month),
        "my_year": count_user(start_of_year)
    })

@app.route('/admin/announcements', methods=['GET', 'POST'])
def admin_announcements():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))  # Secure admin route

    if request.method == 'POST':
        title = request.form.get('title')
        body = request.form.get('message')

        if body:
            new_announcement = Announcement(title=title, body=body)
            db.session.add(new_announcement)
            db.session.commit()
            flash("Announcement posted successfully.")

    # Delete functionality
    delete_id = request.args.get('delete')
    if delete_id:
        ann = Announcement.query.get(delete_id)
        if ann:
            db.session.delete(ann)
            db.session.commit()
            flash("Announcement deleted.")

    announcements = Announcement.query.order_by(Announcement.timestamp.desc()).all()
    return render_template('admin_announcements.html', announcements=announcements)

@app.route('/logout')
def logout():
    session.clear()  # Clear all session data (username, role, etc.)
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    app.run(debug=True)
