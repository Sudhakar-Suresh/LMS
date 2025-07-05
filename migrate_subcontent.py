from app import create_app, db

app = create_app()


def migrate_subcontent():
    with app.app_context():
        # Import models here to avoid circular imports
        from app.models.user import SubContent

        # Create the SubContent table
        db.create_all()
        print("SubContent table created successfully!")


if __name__ == '__main__':
    migrate_subcontent()
