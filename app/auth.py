from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import check_password_hash
from .models import User
from .extensions import db, bcrypt
from flask_login import login_user, logout_user, login_required
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()

# Después:
from .extensions import bcrypt

# Definición del Blueprint para las rutas de autenticación
auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.objects(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('routes.panel'))  # Redirigir al panel después del login
        else:
            flash('Correo o contraseña incorrectos')  # Mensaje de error si las credenciales son incorrectas

    return render_template('login.html')  # Renderiza la página de login

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Las contraseñas no coinciden')  # Flash message si las contraseñas no coinciden
            return redirect(url_for('auth.register'))

        user = User.objects(email=email).first()
        if user:
            flash('Correo ya registrado')  # Flash message si el correo ya existe
            return redirect(url_for('auth.register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(email=email, password=hashed_password)
        new_user.save()
        return redirect(url_for('auth.login'))  # Redirigir al login después de registrar el usuario

    return render_template('register.html')  # Renderiza la página de registro

@auth.route('/logout')
@login_required
def logout():
    logout_user()  # Cierra la sesión del usuario
    return redirect(url_for('auth.login'))  # Redirige al login

