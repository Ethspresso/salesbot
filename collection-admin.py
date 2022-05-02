#!/usr/bin/env python3
import os
import sys
import sqlite3
import argparse

from dotenv import load_dotenv


def query(conn, query):
    """Perform query against an existing SQLite3 connection and return results. Commit changes in case any changes were made.

    :param conn: SQLite3 connection object
    :param query: Query string to execute
    :return: List of tuples returned by SQLite3. List might be empty.
    """
    c = conn.cursor()
    c.execute(query)
    conn.commit()
    result = c.fetchall()
    c.close()
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-a", "--add", default="", help="Collection slug to add to the list"
    )
    parser.add_argument(
        "--remove", default="", help="Collection slug to remove from the list"
    )
    args = parser.parse_args()

    load_dotenv()
    dbfile = os.getenv("SQLITE3_DB")
    if not dbfile:
        print("No database filename in .env, please try again")
        sys.exit(1)
    conn = sqlite3.connect(dbfile)

    if args.add:
        res = query(
            conn,
            f"SELECT collection_slug FROM collections WHERE collection_slug='{args.add}'",
        )
        if len(res) == 0:
            query(
                conn, f"INSERT INTO collections (collection_slug) VALUES ('{args.add}')"
            )
            print(f"Added collection '{args.add}'")
        else:
            print(f"Collection '{args.add}' already on the list")

    if args.remove:
        res = query(
            conn,
            f"SELECT collection_slug FROM collections WHERE collection_slug='{args.remove}'",
        )
        if len(res) != 0:
            query(
                conn, f"DELETE FROM collections WHERE collection_slug='{args.remove}'"
            )
            print(f"Removed collection '{args.remove}'")
        else:
            print(f"Collection '{args.remove}' not found in list")

    # List all collections currently tracked by the bot
    res = query(conn, "SELECT collection_slug FROM collections")
    if len(res) > 0:
        print("Existing collections supported:")
        for c in res:
            print(f" {c[0]}")
