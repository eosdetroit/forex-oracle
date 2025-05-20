import os
from subprocess import Popen, PIPE
from time import sleep
import requests
from requests.adapters import HTTPAdapter, Retry
import json, sys
from datetime import datetime
import logging
import socket
import pushover
from slack_sdk.webhook import WebhookClient
bash_path='/bin/bash'

hostname = socket.gethostname()

if not os.path.exists('config.json'): sys.exit(f'Configuration file does not exist.\nRename example.config.json file to config.json')

with open('config.json', 'r') as file:
    env = json.loads(file.read())

missing_env_vars = [x for x in env['global'] if not env['global'][x]]
if missing_env_vars: sys.exit(f'Please populate config.json. Missing environment variables: {missing_env_vars}\nExiting.')

chain_api_url           = env['global']['chain_api_url']
api_base_url            = env['global']['api_base_url']
api_key                 = env['global']['api_key']
pairs                   = env['global']['pairs']
polling_rate_seconds    = env['global']['polling_rate_seconds']
onchain_symbols         = env['onchain_symbols']
account_name = ''
permission = ''
wallet_password = ''

os.makedirs('logs', exist_ok=True)
os.makedirs('output', exist_ok=True)
logging.basicConfig(filename=f'logs/oracle.log', level=env['logging']['level'])

pushover_client = None
pushover_config_path = ".pushover"

if os.path.exists(pushover_config_path):
    try:
        pushover_client = pushover.PushoverClient(pushover_config_path)
        logging.info("Pushover client initialized successfully.")
    except Exception as e:
        logging.error(f"Failed to initialize Pushover client: {e}")
else:
    logging.warning(f"Pushover config file not found at {pushover_config_path}. Notifications via Pushover will be disabled.")

slack_webhook_url = ""
slack_webhook = WebhookClient(slack_webhook_url) if slack_webhook_url else None

if not slack_webhook:
    logging.warning("Slack webhook URL not set. Notifications via Slack will be disabled.")



s = requests.Session()
retries = Retry(total=3, backoff_factor=1)
s.mount('https://', HTTPAdapter(max_retries=retries))


if len(sys.argv) == 4:
    account_name = sys.argv[1]
    permission = sys.argv[2]
    wallet_password = sys.argv[3]
    publish_mode = True
else:
    publish_mode = False
    print('\nNo arguments provided. Running in data retrieval mode. Writing data to chain is disabled.\n To enable writing to chain pass arguments. ex:\n  python main.py [ACCOUNT_NAME] [PERMISSION] [CLEOS_WALLET_PASSWORD]\n')
    sleep(3)
    print('Starting...')

def send_notification(message: str, message_title: str, message_priority: int, message_expire: int, message_retry: int):
    if pushover_client:
        try:
            pushover_client.send_message(message=message, title=message_title, priority=message_priority, expire=message_expire, retry=message_retry)
        except Exception as e:
            logging.error(f"Failed to send Pushover notification: {e}")

    if slack_webhook:
        try:
            slack_webhook.send(text=f"{message_title}: {message}")
            logging.debug("Notification sent to Slack.")
        except Exception as e:
            logging.error(f"Failed to send Slack notification: {e}")

def unlock_wallet():
    cmd = f'cleos wallet unlock --password {wallet_password}'

    command = f'{cmd}'
    bash = Popen(command, stdout=PIPE, shell=True, executable=bash_path)
    output = bash.communicate()

def oracle_write(payload):
    unlock_wallet()

    cmd = f"cleos -u {chain_api_url} push action delphioracle write '{json.dumps(payload).lower()}' --permission {account_name}@{permission}"

    command = f'{cmd}'
    bash = Popen(command, stdout=PIPE, shell=True, executable=bash_path)
    output = bash.communicate()
    sleep(11)


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
        output[pair]['high'] = pair_data[pair]['values'][0]['high']
        output[pair]['low'] = pair_data[pair]['values'][0]['low']
        output[pair]['close'] = pair_data[pair]['values'][0]['close']
        output[pair]['datetime'] = pair_data[pair]['values'][0]['datetime']
        logging.debug(pair_data[pair])

    with open('output/latest.raw.json', 'w') as file:
        file.write(json.dumps(output))

    oracle_data = {}
    for pair in output:
        if pair in onchain_symbols.keys():
            oracle_data[onchain_symbols[pair]] = output[pair]
        else:
            logging.warning(f'No mapping found for: {pair}')

    payload = {"owner": f"{account_name}", "quotes": []}

    for pair in oracle_data:
        value = float(oracle_data[pair]['close'])
        value = int(value*10000)
        payload['quotes'].append({"pair": pair, "value": value})

    with open('output/payload.json', 'w') as file:
        file.write(json.dumps(payload).lower())

    return payload


def main():
    logging.info(f'[{datetime.now()}] Starting oracle...')
    send_notification(f'Starting...',f'[{hostname}] Starting Forex Oracle', -1, 3600, 0)
    while(True):
        pair_data = get_pair_data(pairs)

        if not pair_data:
            logging.warning(f'[{datetime.now()}] Trying again in 5 minutes...')
            sleep(300)
            continue

        payload = update_latest_data(pair_data)

        if publish_mode:
            i = 0
            while(i<polling_rate_seconds):
                oracle_write(payload)
                sleep(60)
                i += 60

        else:
            sleep(polling_rate_seconds)


if __name__ == '__main__':
    main()
