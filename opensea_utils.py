import time
import requests

from prometheus_client import Counter

# Prometheus metrics tracked by this module
MARKETPLACE_API_CALLS = Counter(
    "marketplace_api_call_counter",
    "Number of API calls made to marketplace API",
    ["marketplace", "collection_name"],
)
MARKETPLACE_EVENTS_FETCHED = Counter(
    "marketplace_event_count",
    "Number of events fetched from the marketplace",
    ["marketplace", "collection_name"],
)

OPENSEA_API_URL = "https://api.opensea.io/api/v1"

# Use these constants for the event_type argument to get_new_events()
EVENT_TYPE_LISTING = "created"
EVENT_TYPE_SALE = "successful"


def get_new_events(
    opensea_api_key,
    event_type,
    start_time,
    last_event_id_seen,
    contract_address=None,
    collection_slug=None,
    collection_name="unknown",
):
    """
    Get new events from the marketplace API

    Returned as a list of event objects in the format they are returned by the marketplace API.
    Ordering of objects in returned list is not guaranteed.

    :param opensea_api_key: Opensea API key
    :param event_type: Event type to fetch, common types are "created" for listings and "successful" for sales
    :param start_time: Unixtime to start fetching events from
    :param last_event_id_seen: Last event ID seen
    :param collection_name: Name of the collection
    :param collection_slug: OpenSea slug of the collection. Can be used instead of contract_address.
    :param contract_address: Ethereum contract address of the collection to query for. Can be used instead of collection_slug.
    :return: List of new events
    """

    events = list()
    new_last_event_id_seen = last_event_id_seen

    identifier = (
        f"asset_contract_address={contract_address}"
        if contract_address
        else f"collection_slug={collection_slug}"
    )
    try:
        headers = {"X-API-KEY": opensea_api_key, "Accept": "application/json"}
        res = requests.get(
            f"{OPENSEA_API_URL}/events?{identifier}&event_type={event_type}&only_opensea=false&occurred_before={start_time}",
            headers=headers,
        )
        MARKETPLACE_API_CALLS.labels(
            marketplace="OpenSea", collection_name=collection_name
        ).inc()
        res.raise_for_status()
    except Exception as e:
        raise ValueError(f"Hit exception for Opensea API: {e}")

    data = res.json()
    prev_cursor = data["previous"]
    for event in data["asset_events"]:
        if int(event["id"]) > int(last_event_id_seen):
            events.append(event)
            if event["id"] > new_last_event_id_seen:
                new_last_event_id_seen = event["id"]

    while prev_cursor:
        try:
            headers = {"X-API-KEY": opensea_api_key, "Accept": "application/json"}
            res = requests.get(
                f"{OPENSEA_API_URL}/events?{identifier}&event_type={event_type}&only_opensea=false&cursor={prev_cursor}",
                headers=headers,
            )
            MARKETPLACE_API_CALLS.labels(
                marketplace="OpenSea", collection_name=collection_name
            ).inc()
            res.raise_for_status()
        except Exception as e:
            raise ValueError(f"Hit exception for Opensea API: {e}")

        data = res.json()
        for event in data["asset_events"]:
            if int(event["id"]) > int(last_event_id_seen):
                events.append(event)
                if event["id"] > new_last_event_id_seen:
                    new_last_event_id_seen = event["id"]
        prev_cursor = data["previous"]

    MARKETPLACE_EVENTS_FETCHED.labels(
        marketplace="OpenSea", collection_name=collection_name
    ).inc(len(events))

    return events, new_last_event_id_seen
