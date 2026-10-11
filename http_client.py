"""Bound every synchronous HTTP call; call blocking functions from worker threads."""
import requests


def http_get(url, **kwargs):
    kwargs.setdefault("timeout", (5, 15))
    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response
