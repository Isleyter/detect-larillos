from flask_login import UserMixin # type: ignore
from mongoengine import Document, StringField, DateTimeField, IntField, FloatField  # type: ignore # TimeField no necesario

class User(Document, UserMixin):
    email = StringField(required=True, unique=True, max_length=100)
    password = StringField(required=True, max_length=100)

    meta = {'collection': 'usuarios'}  # <- Aquí defines el nombre exacto de la colección en MongoDB

    def get_id(self):  # Necesario para Flask-Login
        return str(self.id)

class Monitoreo(Document):
    monitoreo_id = IntField(required=True, unique=True)  # NUEVO CAMPO
    fecha = DateTimeField()
    hora_inicio = StringField()  # MongoEngine no tiene TimeField puro, usamos string
    hora_fin = StringField()
    total_ladrillos = IntField()
    ladrillos_buenos = IntField()
    ladrillos_malos = IntField()
    precision = FloatField()
    tiempo_promedio_fisura = FloatField(null=True)
    pdf_path = StringField()

    meta = {'collection': 'monitoreos'}  # <- Nombre de colección explícito
