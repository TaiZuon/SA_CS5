from app.config.database import get_connection

def reset_db():
  print("[🔄] Resetting database...")

  # Establish a connection to the database
  connection = get_connection()
  cursor = connection.cursor()

  print("[⚙️] Disabling foreign key checks...")
  cursor.execute("SET FOREIGN_KEY_CHECKS=0;")

  print("[🧹] Dropping existing tables if they exist...")
  cursor.execute("DROP TABLE IF EXISTS commit;")
  cursor.execute("DROP TABLE IF EXISTS releases;")
  cursor.execute("DROP TABLE IF EXISTS repo;")

  print("[🛠️] Recreating tables...")

  # Recreate the 'repo' table
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS repo (
      id INT AUTO_INCREMENT NOT NULL UNIQUE,
      user TEXT NOT NULL,
      name TEXT NOT NULL,
      PRIMARY KEY (id)
    );
  """)
  print("✅ Created table: repo")

  # Recreate the 'releases' table
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS releases (
      id INT NOT NULL UNIQUE,
      content TEXT NOT NULL,
      repoID INT NOT NULL,
      PRIMARY KEY (id),
      FOREIGN KEY (repoID) REFERENCES repo(id)
    );
  """)
  print("✅ Created table: releases")

  # Recreate the 'commit' table
  cursor.execute("""
    CREATE TABLE IF NOT EXISTS commit (
      hash TEXT NOT NULL,
      message TEXT NOT NULL,
      releaseID INT NOT NULL,
      FOREIGN KEY (releaseID) REFERENCES releases(id)
    );
  """)
  print("✅ Created table: commit")

  print("[✅] Re-enabling foreign key checks...")
  cursor.execute("SET FOREIGN_KEY_CHECKS=1;")

  # Commit changes and close connection
  connection.commit()
  cursor.close()
  connection.close()
  print("[🎉] Database reset complete.")