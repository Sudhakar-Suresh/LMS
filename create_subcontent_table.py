import sqlite3

# Connect to the database
conn = sqlite3.connect('app/lms.db')
cursor = conn.cursor()

# Create the SubContent table
cursor.execute('''
CREATE TABLE IF NOT EXISTS sub_content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(100) NOT NULL,
    content TEXT,
    content_type VARCHAR(20) NOT NULL DEFAULT 'text',
    file_path VARCHAR(255),
    topic_id INTEGER NOT NULL,
    "order" INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (topic_id) REFERENCES topic (id)
)
''')

# Commit the changes and close the connection
conn.commit()
conn.close()

print("SubContent table created successfully!")
