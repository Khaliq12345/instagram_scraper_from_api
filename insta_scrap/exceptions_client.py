import requests

exceptions = (
    requests.Timeout,
    requests.ConnectionError,
    requests.ConnectTimeout,
    requests.ReadTimeout,
)
