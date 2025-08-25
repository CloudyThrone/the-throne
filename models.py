from extensions import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    role = db.Column(db.String(20), default='user')
    balance = db.Column(db.Float, default=0.0)
    phone = db.Column(db.String(20))


class Withdrawals(db.Model):
    __tablename__ = 'withdrawals'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(50))
    time = db.Column(db.String(50))
    amount = db.Column(db.Float, nullable=False)
    balance = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')
    phone = db.Column(db.String(20))


class Referrals(db.Model):
    __tablename__ = 'referrals'
    id = db.Column(db.Integer, primary_key=True)
    inviter_username = db.Column(db.String(50), nullable=False)
    invitee_username = db.Column(db.String(50), nullable=False)
    referer_username = db.Column(db.String(50))  # optional
    profit = db.Column(db.Float, default=0.0)


class PendingUsers(db.Model):
    __tablename__ = 'pending_users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='pending')


class InviteLog(db.Model):
    __tablename__ = 'invite_log'
    id = db.Column(db.Integer, primary_key=True)
    inviter_username = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class TopInviterTracker(db.Model):
    __tablename__ = 'top_inviter_tracker'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    crown_count = db.Column(db.Integer, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)


class Announcement(db.Model):
    __tablename__ = 'announcements'  # matches your existing table
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=True)
    body = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
