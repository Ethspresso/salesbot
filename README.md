# Simple Discord sales bot for NFT collections

This bot checks the marketplace regularly and posts new sales to a Discord channel using a webhook. It was built to support multiple collections and tailored to the needs of the 1/1 art community. It's free to use by anyone for any NFT collection.

The bot only supports OpenSea for the moment. You tell it to monitor named collections on OpenSea and it'll post a message for every sale it detects. The message contains the image of the NFT and a bit of information about buyer, seller, collection and price.

On startup the bot posts about sales that happened up to a few hours ago. This lookback window is configurable. When the bot is running it keeps track of sales that it has reported already and only posts about new sales that happen. This information is not persisted though, so if something happens that causes the bot to restart multiple times, it'll post the same sales multiple times. Be aware that the bot has not been tested for high transaction volume collections so there might be edge cases and bugs for very busy collections. PRs are welcome to make the bot more robust. I have limited capacity to fix issues though so you are highly encouraged to submit a PR instead of just opening an issue.

## Requirements

To use this bot, you need the following:
  * OpenSea API key
  * Ability to add Discord webhooks for the channel you want the bot to post to
  * The name of the collection(s) you want to monitor sales for
  * A working Python environment (see below for details)

It is recommended to launch the bot using something like Docker or SystemD to ensure it can run 24/7 without depending on an open shell. You can of course try it out in a shell first and even use `screen`. The bot does not fork to the background or anything, it's just a forever-running while loop in a Python script.

## Quick start guide

1. Clone the Git repo
2. `pipenv install`
3. Copy the .env template (below) into `.env`
4. Add your OpenSea API key and Discord webhook URL in `.env`
5. Add one or more Opensea collection slugs using `./collection-admin.py -a`
6. Launch the bot with `python3 salesbot.py`

## Python Requirements

Python module dependencies:
  * requests
  * discord.py
  * python-dotenv
  * prometheus-client

All dependencies can be installed using Pipenv:
```
$ pipenv install
```

If your Python version is too old you'll get this error:
```
Warning: Python 3.9 was not found on your system…
```

The recommended way to fix this is to use PyEnv to install additional versions of Python without modifying your system-provided Python:
```
$ pyenv install 3.9
```

Tell PyEnv to use a particular version for the local dir like this:
```
$ pyenv local 3.9.10
```

Then rerun the Pipenv install command above.

## Bot Configuration

The main configuration is added to a `.env` file in the same folder the bot runs. Here is a template that shows which options are available and what needs to be filled in:
```
#
# Discord configuration
#
# Webhook URL to write to a given Discord channel
# Which channel to post to is decided by the admin creating the webhook
DISCORD_WEBHOOK_URL=""

#
# Marketplace configuration
#
# API key is required to use the OpenSea APIs extensively
OPENSEA_API_KEY=""

#
# Bot behavior
#
# How often to check each collection for new sales, in seconds (default 60s)
CHECK_INTERVAL=60
# Filename of SQLite3 database with collection details
SQLITE3_DB="salesbot.db"
# Port number to bind to for Prometheus metrics (default 9110)
PROMETHEUS_METRIC_PORT="9110"
```

## Collection management

OpenSea collections can be added and removed from the list of watched collections using `collection-admin.py`. Run the script with `-h` to see the arguments it supports. You can add and remove collections while the bot is running, it will automatically pick up on changes. No need to restart the bot.

The collections are added as "collection slugs", which is the last part of the collection URL. So for example for https://opensea.io/collection/exploding-stars-vol2 the collection slug is `exploding-stars-vol2`. That's the name you need to add using `collection-admin.py`.

## Metrics and monitoring

Prometheus metrics are exposed on the configured port number. A simple health check to ensure the bot is running at all times is to monitor that this port is open.

The metrics exposed by the bot are at least the following:
  * "marketplace_api_call_counter" with labels "marketplace", "collection_name"
  * "marketplace_listing_event_count" with labels "marketplace", "collection_name"

These metrics record the number of API calls made to each marketplace for each collection, and how many events (sales) have been fetched by the bot so far.


## Questions

You can reach me on https://twitter.com/ethspresso 
