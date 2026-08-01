import getpass

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User


def main():
    app = create_app()
    username = input("Admin username: ").strip()
    email = input("Admin email: ").strip().lower()
    password = getpass.getpass("Admin password (min 8 chars): ")
    if len(password) < 8:
        raise SystemExit("Password must be at least 8 characters")
    with app.app_context():
        if User.query.filter((User.username == username) | (User.email == email)).first():
            raise SystemExit("Username or email already exists")
        db.session.add(User(username=username, email=email, password_hash=generate_password_hash(password), is_admin=True))
        db.session.commit()
    print("Admin created")


if __name__ == "__main__":
    main()
