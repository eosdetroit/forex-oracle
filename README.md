# forex-oracle

For retrieval of forex pair pricing data.

Currently dumps latest available from twelvedata API to output folder, transforms to delphioracle payload, and calls delphioracle::write.

If no arguments are provided on launch, it will only retrieve data. 

## Getting started
1.) `cp example.config.json config.json`

2.) Populate api_key (for twelvedata API).

3.) Optional: Modify polling rate (default: 1800 seconds) & desired pairs for retrieval.


## Run

Data retrieval mode:
will dump oracle payload to file.
Run: `python main.py`

Publish mode:
will write oracle payload to chain.
`python main.py [account_name] [permission] [cleos_password]`

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
