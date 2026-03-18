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
