import psycopg2

conn = psycopg2.connect(
    "postgresql://postgres:tybpost%40%2356*@localhost:5432/nutrition_ai"
)

print("✅ Connected successfully!")

conn.close()