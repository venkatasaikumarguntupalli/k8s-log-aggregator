# k8s-log-aggregator

k8s-log-aggregator is a A lightweight Python CLI tool that simplifies debugging in Kubernetes by collecting and aggregating logs from multiple pods using label selectors. It supports parallel log fetching, regex filtering, and JSON/file export, making it easier to analyze distributed system issues.

## Featurs

- Fetch logs from multiple pods using a label selector
- Aggregate logs into one readable output
- Parallel log fetching for faster execution
- Optional container selection
- Fetch previous container logs for crash debugging
- Filter logs using regex
- Limit logs using `--tail`
- Fetch recent logs using `--since`
- Save logs to separate files
- Export logs as JSON

## Requirements

- Python 3.9+
- kubectl installed and configured
- Access to a Kubernetes cluster

## Installation

```bash
git clone https://github.com/venkatasaikumarguntupalli/k8s-log-aggregator.git
cd k8s-log-aggregator
pip install -r requirements.txt
```

## Usage

Aggregate logs in terminal

```bash
python k8s_log_aggregator.py -n default -l app=my-service
```

Filter only error logs

```bash
python k8s_log_aggregator.py -n default -l app=my-service --grep "ERROR|Exception"
```

Fetch logs from the last 10 minutes

```bash
python k8s_log_aggregator.py -n default -l app=my-service --since 10m
```

Fetch previous logs from crashed containers

```bash
python k8s_log_aggregator.py -n default -l app=my-service --previous
```

Save logs to files

```bash
python k8s_log_aggregator.py -n default -l app=my-service --json-output logs.json
```

Export logs as JSON

```bash
python k8s_log_aggregator.py -n default -l app=my-service --json-output logs.json
```

## Motivation

Debugging distributed services in Kubernetes often requires checking logs across multiple pods one by one. This tool simplifies that process by aggregating logs in a single place and adding basic filtering and export options.
