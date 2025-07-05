from app import create_app, db
from datetime import datetime


def run_migration():
    app = create_app()
    with app.app_context():
        try:
            # Check if the column exists
            result = db.session.execute(
                "PRAGMA table_info(messages)").fetchall()
            columns = [row[1] for row in result]

            if 'created_at' not in columns:
                print("Adding 'created_at' column to messages table...")
                # Add the created_at column with default value of current timestamp
                db.session.execute(
                    "ALTER TABLE messages ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                db.session.commit()
                print("Migration completed successfully!")
            else:
                print("The 'created_at' column already exists in the messages table.")
        except Exception as e:
            db.session.rollback()
            print(f"Error during migration: {str(e)}")


if __name__ == "__main__":
    run_migration()
