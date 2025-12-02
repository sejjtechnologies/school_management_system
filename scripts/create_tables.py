from app import app
from models.user_models import db

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print('Created/verified all tables via SQLAlchemy metadata.')
