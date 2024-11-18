Initial Setup
Ensure Flask-Migrate is installed: Make sure Flask-Migrate is included in your project. If not, install it using:

    pip install Flask-Migrate

Creating a New Migration
Whenever you make changes to your models (e.g., adding or removing fields, creating new models), perform the following steps:

Generate a Migration: Run the following command to create a new migration file:

    flask db migrate -m "Description of changes"

Applying Migrations
After creating a migration, you need to apply it to your database:
Upgrade the Database: Run the following command to apply the migration:

    flask db migrate -m "Description of changes"
    flask db upgrade