import queue
import httpx

import ssl
import certifi

ctx = ssl.create_default_context(cafile=certifi.where())

signal_queue = queue.Queue()


http_client = httpx.Client(verify=ctx)
