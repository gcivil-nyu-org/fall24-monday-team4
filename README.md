# Postgres Setup Instructions

## Install Required Unix/Linux Packages

1. `sudo apt update`
2. `sudo apt install postgresql postgresql-contrib`
3. `sudo apt-get install postgis`
4. `sudo apt-get install python3-psycopg2 libgeos-dev libproj-dev libgdal-dev libffi-dev`

## Install Required Python Environment Libraries

`pip install -r "requirements.txt"`

## This sets up the PostgreSQL database and user for Django

### User and database information

```json
DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": "routepals",
        "USER": "geo",
        "PASSWORD": "12345",
        "HOST": "localhost",
        "PORT": "5432",
    },
}
```

### Create the PostgreSQL user

`sudo -u postgres createuser --interactive -P geo`

### Make geo a superuser

`sudo -u postgres psql -c "ALTER USER geo WITH SUPERUSER;"`

### Create the PostgreSQL database

`sudo -u postgres createdb -O geo routepals`

### Add the PostGIS extension

`sudo -u postgres psql -d routepals -c "CREATE EXTENSION postgis;"`

### Grant all privileges on the database to geo

`sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE routepals TO geo;"`

### Change ownership of all tables, sequences, and views in the database to geo

`sudo -u postgres psql -d routepals -c "ALTER DATABASE routepals OWNER TO geo;"`

### Run your migrations to ensure tables are created

`python manage.py makemigrations`
`python manage.py migrate`

### Ensure Django has switched from SQLite to PostgreSQL

Check the Current Database: Run the following command in your Django shell to confirm which database is being used.

`python manage.py dbshell`

If it connects to PostgreSQL, you'll see the psql prompt. If it’s still SQLite, you’ll see nothing or an error.
