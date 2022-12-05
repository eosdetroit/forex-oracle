import os
from subprocess import Popen, PIPE
from time import sleep
import requests
from requests.adapters import HTTPAdapter, Retry
import json, sys
from datetime import datetime
import logging
bash_path="/bin/bash"

if not os.path.exists('config.json'): sys.exit(f'Configuration file does not exist.\nRename example.config.json file to config.json')

with open('config.json', 'r') as file:
    env = json.loads(file.read())

missing_env_vars = [x for x in env['global'] if not env['global'][x]]
if missing_env_vars: sys.exit(f'Please populate config.json. Missing environment variables: {missing_env_vars}\nExiting.')

api_base_url            = env['global']['api_base_url']
api_key                 = env['global']['api_key']
pairs                   = env['global']['pairs']
polling_rate_seconds    = env['global']['polling_rate_seconds']

os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)
logging.basicConfig(filename=f'logs/oracle.log', level=env['logging']['level'])
logging.info(f'[{datetime.now()}] Starting oracle...')

s = requests.Session()
retries = Retry(total=3, backoff_factor=1)
s.mount('https://', HTTPAdapter(max_retries=retries))

def get_pair_data(pairs):
    symbols = '' 
    for pair in pairs:
        symbols += f'{pair},'

    url = f'{api_base_url}/time_series?symbol={symbols}&&interval=1min&apikey={api_key}'

    response = s.get(url)
    response_data = json.loads(response.text)
    
    if response.status_code != 200:
        logging.error(f'[{datetime.now()}] status_code: {response.status_code} received from API. Retries exhausted.')
        return None

    status_error = [x for x in response_data if response_data[x]['status'] != 'ok']

    if status_error:
        logging.error(f'[{datetime.now()}] Error while retrieving pairs: {status_error} - \n{response_data}')
        return None

    return response_data

def update_latest_data(pair_data):
    output = {}
    for pair in pair_data:
        output[pair] = {}
        output[pair]['high'] = pair_data[pair]["values"][0]["high"]
        output[pair]['low'] = pair_data[pair]["values"][0]["low"]
        output[pair]['close'] = pair_data[pair]["values"][0]["close"]
        output[pair]['datetime'] = pair_data[pair]["values"][0]["datetime"]
        logging.debug(pair_data[pair])

    with open('output/latest', 'w') as file:
        file.write(json.dumps(output))

    return output


def main():
    while(True):
        pair_data = get_pair_data(pairs)

        if not pair_data:
            logging.warn(f'[{datetime.now()}] Trying again in 5 minutes...')
            sleep(300)
            continue

        output = update_latest_data(pair_data)
        #unlock_wallet()
        #publish_feed(output)

        sleep(polling_rate_seconds)


if __name__ == "__main__":
    main()
