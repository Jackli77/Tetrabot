import os
import psycopg2

#Connect to DB
DATABASE_URL = "postgres://eccexmdcwmfbfs:ffc3c2b5fdee5036a8ccc050911f405773c568ec757870655c1142e9f3ace6c6@ec2-3-248-4-172.eu-west-1.compute.amazonaws.com:5432/d2tvutmq0s0kd0"
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

def initialize():
    # Open a cursor to perform database operations
    cur = conn.cursor()
