# forex-oracle

For retrieval of forex pair pricing data.

Currently dumps latest available data to output/latest. Does not process this or write to network via cleos yet.

## Getting started
1.) `cp example.config.json config.json`

2.) Populate api_key (for twelvedata API).

3.) Optional: Modify polling rate (default: 1800 seconds) & desired pairs for retrieval.


## Run
`python main.py`

## Logging

Configuration default logging level set to INFO (20).

| Level  | Config Value |
| ------------- |:------:|
| CRITICAL      | 50     |
| ERROR         | 40     |
| WARNING       | 30     |
| INFO          | 20     |
| DEBUG         | 10     |


## TODO
* Provide default algorithm to produce payload and write to chain