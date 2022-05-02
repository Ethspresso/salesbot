import os
import sys
import math
import time
import discord
import logging
import sqlite3
import argparse
import datetime

from dotenv import load_dotenv
from prometheus_client import start_http_server
from collections import defaultdict

from opensea_utils import get_new_events, EVENT_TYPE_SALE


def get_collection_slugs(sqlite3_db):
    """Query database for collections to check and return list of collection slugs"""
    conn = sqlite3.connect(sqlite3_db)
    c = conn.cursor()
    c.execute("SELECT collection_slug FROM collections")
    collection_slugs = [row[0] for row in c.fetchall()]
    conn.close()
    return collection_slugs


def main(opensea_api_key, webhook_url, sqlite3_db, check_interval):
    webhook = discord.Webhook.from_url(
        webhook_url, adapter=discord.RequestsWebhookAdapter()
    )

    last_event_id_seen = defaultdict(int)

    # Throw away events older than this
    # This is mainly used at startup to avoid reposting old sales
    EVENT_MAX_AGE = datetime.timedelta(hours=6)

    while True:
        events = []
        for collection_slug in get_collection_slugs(sqlite3_db):
            now = int(time.time())
            try:
                logging.info(
                    f"Querying for new events for {collection_slug} up until {now} filtering for events after {last_event_id_seen[collection_slug]}"
                )
                new_events, new_last_id = get_new_events(
                    opensea_api_key=opensea_api_key,
                    event_type=EVENT_TYPE_SALE,
                    collection_name=collection_slug,
                    collection_slug=collection_slug,
                    start_time=now,
                    last_event_id_seen=last_event_id_seen[collection_slug],
                )
                last_event_id_seen[collection_slug] = new_last_id
            except Exception as e:
                logging.warning(e)
                time.sleep(1)
                continue

            if new_events:
                events.extend(new_events)

        if events:
            for event in sorted(
                events, key=lambda event: event["transaction"]["timestamp"]
            ):
                if (
                    datetime.datetime.today()
                    - datetime.datetime.strptime(
                        event["transaction"]["timestamp"], "%Y-%m-%dT%H:%M:%S"
                    )
                    < EVENT_MAX_AGE
                ):
                    try:
                        price = int(event["total_price"]) / math.pow(
                            10, event["payment_token"]["decimals"]
                        )
                        symbol = event["payment_token"]["symbol"]
                        sold_at = event["transaction"]["timestamp"]

                        # Look up OpenSea username of buyer and seller
                        # Fall back to first six characters of address if no username is found
                        buyer = (
                            f"{event['winner_account']['user']['username']}"
                            if event["winner_account"]["user"]["username"]
                            else f"{event['winner_account']['address'][2:8].upper()}"
                        )
                        seller = (
                            f"{event['seller']['user']['username']}"
                            if event["seller"]["user"]["username"]
                            else f"{event['seller']['address'][2:8].upper()}"
                        )

                        # Detect bundles
                        if not event["asset"] and event["asset_bundle"]:
                            url = f"{event['asset_bundle']['permalink']}"
                            title = f"{len(event['asset_bundle']['assets'])} pieces in {event['asset_bundle']['name']} sold by {seller}"
                            image_url = event["asset_bundle"]["assets"][0]["image_url"]
                            collection_name = event["asset_bundle"]["assets"][0][
                                "collection"
                            ]["name"]
                        else:
                            # Common case: One asset only
                            title = f"{event['asset']['name']} sold by {seller}"
                            url = event["asset"]["permalink"]
                            image_url = event["asset"]["image_url"]
                            collection_name = event["asset"]["collection"]["name"]
                    except Exception as e:
                        logging.warning(f"Failed to parse event due to {e}")
                        continue

                    # Format message
                    message = (
                        discord.Embed(title=title, url=url)
                        .set_image(url=image_url)
                        .add_field(
                            name="Collection", value=collection_name, inline=True
                        )
                        .add_field(name="Buyer", value=buyer, inline=True)
                        .add_field(name="Price", value=f"{price} {symbol}", inline=True)
                        .set_footer(text=f"Sold at {sold_at}")
                    )

                    # Post to Discord channel
                    try:
                        webhook.send(embed=message)
                    except Exception as e:
                        logging.error(
                            f"Hit exception for Discord webhook, ignored message due to: {e}"
                        )

                    time.sleep(0.1)

        time.sleep(int(check_interval))


if __name__ == "__main__":
    # Command-line arguments for extra options while testing, like debug output
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d-%b-%y %H:%M:%S",
        stream=sys.stdout,
    )

    #
    # Load main service configuration from .env
    #
    load_dotenv()
    # API key is required to use the OpenSea APIs extensively
    OPENSEA_API_KEY = os.getenv("OPENSEA_API_KEY")
    # Webhook URL to write to a given Discord channel
    # Which channel to post to is decided by the admin creating the webhook
    DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
    # Port to bind to, for exposing metrics to Prometheus. Defaults to port 9110
    PROMETHEUS_METRIC_PORT = os.getenv("PROMETHEUS_METRIC_PORT", "9110")
    # How often to check each collection for new sales, in seconds. Default 60s.
    CHECK_INTERVAL = os.getenv("CHECK_INTERVAL", "60")
    # Filename of SQLite3 database with collection names.
    SQLITE3_DB = os.getenv("SQLITE3_DB")

    if not all([OPENSEA_API_KEY, DISCORD_WEBHOOK_URL, SQLITE3_DB]):
        logging.error("Incomplete configuration, please check .env file and try again")
        sys.exit(1)

    start_http_server(int(PROMETHEUS_METRIC_PORT))
    main(OPENSEA_API_KEY, DISCORD_WEBHOOK_URL, SQLITE3_DB, CHECK_INTERVAL)
