#!/usr/bin/env python3
"""
Database reset script - Drops all tables and recreates them with the new schema
WARNING: This will delete all data!
"""
import os
from sqlalchemy import text
from app.db import engine, Base
from app.models import GeoFile, Feature

print("=" * 60)
print("Database Reset Script")
print("WARNING: This will delete all existing data!")
print("=" * 60)

response = input("Are you sure you want to continue? (yes/no): ")
if response.lower() != 'yes':
    print("Cancelled.")
    exit(0)

print("\nDropping all tables...")
try:
    # Drop all tables
    Base.metadata.drop_all(bind=engine)
    print("✓ All tables dropped")
except Exception as e:
    print(f"Note: {e}")

print("\nCreating PostGIS extension...")
with engine.begin() as conn:
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        print("✓ PostGIS extension enabled")
    except Exception as e:
        print(f"Note: {e}")

print("\nCreating tables...")
try:
    Base.metadata.create_all(bind=engine)
    print("✓ All tables created successfully")
except Exception as e:
    print(f"✗ Error creating tables: {e}")
    exit(1)

print("\n" + "=" * 60)
print("Database reset complete!")
print("=" * 60)

