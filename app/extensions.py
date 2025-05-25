from flask_mongoengine import MongoEngine # type: ignore
from flask_login import LoginManager # type: ignore
from flask_bcrypt import Bcrypt # type: ignore


db = MongoEngine()
login_manager = LoginManager()
bcrypt = Bcrypt()
#migrate = Migrate()  # puedes omitirlo si no usas migraciones
