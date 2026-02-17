"""
Authentication Module for Question Paper Application

Provides password hashing, verification, and session management utilities.
"""

from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from flask import session, redirect, url_for, flash
import sqlite3
import os
from datetime import datetime

DATABASE_PATH = os.environ.get('DATABASE_PATH', 'question_bank.db')


def hash_password(password: str) -> str:
    """
    Hash a password using pbkdf2:sha256
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
    """
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        password: Plain text password to verify
        password_hash: Stored password hash
        
    Returns:
        True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


def authenticate_user(username: str, password: str, role: str) -> dict:
    """
    Authenticate a user by username, password, and role
    
    Args:
        username: User's username
        password: User's plain text password
        role: Either 'teacher' or 'student'
        
    Returns:
        Dict with user info if authenticated, None otherwise
        {'id': user_id, 'username': username, 'full_name': name, 'role': role}
    """
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    table = 'teachers' if role == 'teacher' else 'students'
    
    cursor.execute(f'''
        SELECT id, username, password_hash, full_name, email
        FROM {table}
        WHERE username = ?
    ''', (username,))
    
    user = cursor.fetchone()
    
    if user and verify_password(password, user[2]):
        # Update last login
        cursor.execute(f'''
            UPDATE {table}
            SET last_login = ?
            WHERE id = ?
        ''', (datetime.now(), user[0]))
        conn.commit()
        conn.close()
        
        return {
            'id': user[0],
            'username': user[1],
            'full_name': user[3],
            'email': user[4],
            'role': role
        }
    
    conn.close()
    return None


def create_user(username: str, password: str, full_name: str, email: str, role: str) -> bool:
    """
    Create a new user account
    
    Args:
        username: Unique username
        password: Plain text password (will be hashed)
        full_name: User's full name
        email: User's email address
        role: Either 'teacher' or 'student'
        
    Returns:
        True if user created successfully, False otherwise
    """
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        table = 'teachers' if role == 'teacher' else 'students'
        user_id = f"{role[0]}{username[:3]}{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        cursor.execute(f'''
            INSERT INTO {table} (id, username, password_hash, full_name, email, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, hash_password(password), full_name, email, datetime.now()))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username or email already exists
        return False


def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def teacher_required(f):
    """Decorator to require teacher role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'teacher':
            flash('Access denied. Teacher privileges required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def student_required(f):
    """Decorator to require student role for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        if session.get('role') != 'student':
            flash('Access denied. Student privileges required.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function
