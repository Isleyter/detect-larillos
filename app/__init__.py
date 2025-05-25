from flask import Flask
from .extensions import db, login_manager, bcrypt
from config import Config  # asegúrate de que config.py esté fuera del directorio app

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)  # ✅ esta línea debe estar DENTRO de create_app

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    from .models import User
    from .routes import routes as routes_blueprint
    from .auth import auth as auth_blueprint
    app.register_blueprint(routes_blueprint)
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    @login_manager.user_loader
    def load_user(user_id):
        return User.objects(id=user_id).first()

    return app
