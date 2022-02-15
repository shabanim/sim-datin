import json
import requests
from requests.exceptions import HTTPError

AUTH_TOKEN = "Splunk 6e895ba7-2d42-46a6-8312-e76ec21e8e08"

def upload(event_entry):
    splunk_headers = {'Authorization': AUTH_TOKEN,
                      'Content-Type': 'application/json'}

    data = json.dumps({"sourcetype": "manual", "event": event_entry})
    try:
        response = requests.post('https://engsplunk.intel.com:8088/services/collector/event', headers=splunk_headers,
                                 data=data, verify=False)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:  # pylint: disable=broad-except
        print(f'Other error occurred: {err}')

