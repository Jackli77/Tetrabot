import os
import psycopg2

#Connect to DB
DATABASE_URL = os.environ['DATABASE_URL']
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

def initialize():
    # Open a cursor to perform database operations
    cur = conn.cursor()
