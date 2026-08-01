# Database migrations

Production deployments use Flask-Migrate/Alembic. Set `AUTO_CREATE_DB=0`, then run:

```bash
flask --app manage.py db init
flask --app manage.py db migrate -m "schema change"
flask --app manage.py db upgrade
```

Run `db init` only once. Commit generated migration files.
