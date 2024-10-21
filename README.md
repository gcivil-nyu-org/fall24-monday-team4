# The easiest way to get started with PostgreSQL on the Mac

1. Download Postgres.app from https://postgresapp.com/. Postgres.app contains both PostgreSQL and its extension PostGIS. I downloaded Postgres.app with PostgreSQL 16 (Universal).

2. After installing Postgres.app, add the following to your `.bash_profile` so you can run the package’s programs from the command-line. Replace `X.Y` with the version of PostgreSQL in the Postgres.app you installed:  
   `export PATH=$PATH:/Applications/Postgres.app/Contents/Versions/X.Y/bin`.  
   You can check if the path is set up correctly by typing `which psql` at a terminal prompt.

3. You will also need to install `gdal` and `libgeoip` with Homebrew.

# Alternative option:
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

Note: You might need to run these commands after setting up the databases:  
`python3 manage.py makemigrations`  
`python3 manage.py migrate`  
`python3 manage.py dbshell`