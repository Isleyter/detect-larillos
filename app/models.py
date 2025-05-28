from flask_login import UserMixin  # type: ignore
from mongoengine import Document, StringField, DateTimeField, IntField, FloatField  # type: ignore

class User(Document, UserMixin):
    email = StringField(required=True, unique=True, max_length=100)
    password = StringField(required=True, max_length=100)

    meta = {'collection': 'usuarios'}

    def get_id(self):
        return str(self.id)


class Monitoreo(Document):
    usuario = StringField(required=True)
    fecha = DateTimeField(required=True)
    hora_inicio = StringField(required=True)
    hora_fin = StringField(required=True)
    total_ladrillos = IntField(required=True)
    ladrillos_buenos = IntField(required=True)
    ladrillos_malos = IntField(required=True)
    precision = FloatField(required=True)
    tiempo_promedio_fisura = FloatField()
    pdf_path = StringField()

    meta = {'collection': 'reportes'}

    def to_json(self):
        return {
            "id": str(self.id),
            "usuario": self.usuario,
            "fecha": self.fecha.isoformat(),
            "hora_inicio": self.hora_inicio,
            "hora_fin": self.hora_fin,
            "total_ladrillos": self.total_ladrillos,
            "ladrillos_buenos": self.ladrillos_buenos,
            "ladrillos_malos": self.ladrillos_malos,
            "precision": self.precision,
            "tiempo_promedio_fisura": self.tiempo_promedio_fisura,
            "pdf_path": self.pdf_path
        }
