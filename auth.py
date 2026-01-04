"""
auth.py

Decoradores para proteger rotas e verificar permissões.
"""

from functools import wraps
from flask import session, redirect, url_for, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        # Trata None ou dict vazio como não logado
        if not user:
            flash('Por favor, faça login para acessar esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get("user")
        if not user:
            flash('Por favor, faça login.', 'warning')
            return redirect(url_for('login'))

        role = user.get('role')
        if role != 'admin':
            flash('Acesso negado. Apenas administradores.', 'danger')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function
