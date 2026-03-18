import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

import click


def run_kubectl_command(args: List[str]) -> subprocess.CompletedProcess:
    """
    Run a kubectl command and return the completed process.
    """
    try:
        return subprocess.run(
            ["kubectl"] + args,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        click.echo("Error: kubectl is not installed or not found in PATH.", err=True)
        sys.exit(1)


def get_pods(namespace: str, selector: str) -> List[str]:
    """
    Get pod names in the given namespace matching the label selector.
    """
    result = run_kubectl_command(
        ["get", "pods", "-n", namespace, "-l", selector, "-o", "json"]
    )

    if result.returncode != 0:
        click.echo(f"Error fetching pods:\n{result.stderr}", err=True)
        sys.exit(1)

    try:
        pod_json = json.loads(result.stdout)
        return [item["metadata"]["name"] for item in pod_json.get("items", [])]
    except (json.JSONDecodeError, KeyError) as exc:
        click.echo(f"Error parsing pod list: {exc}", err=True)
        sys.exit(1)


def fetch_logs_for_pod(
    pod_name: str,
    namespace: str,
    container: Optional[str],
    tail: int,
    previous: bool,
    since: Optional[str],
) -> Dict[str, str]:
    """
    Fetch logs for a single pod.
    Returns a dict with pod name, status, and content/error.
    """
    args = ["logs", pod_name, "-n", namespace, "--tail", str(tail)]

    if container:
        args.extend(["-c", container])

    if previous:
        args.append("--previous")

    if since:
        args.extend(["--since", since])

    result = run_kubectl_command(args)

    if result.returncode != 0:
        error_message = result.stderr.strip() or "Unknown error while fetching logs."
        return {
            "pod": pod_name,
            "status": "error",
            "content": error_message,
        }

    return {
        "pod": pod_name,
        "status": "success",
        "content": result.stdout,
    }


def fetch_logs_parallel(
    pods: List[str],
    namespace: str,
    container: Optional[str],
    tail: int,
    previous: bool,
    since: Optional[str],
    max_workers: int = 5,
) -> List[Dict[str, str]]:
    """
    Fetch logs for multiple pods in parallel.
    """
    results: List[Dict[str, str]] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                fetch_logs_for_pod,
                pod,
                namespace,
                container,
                tail,
                previous,
                since,
            ): pod
            for pod in pods
        }

        for future in as_completed(future_map):
            results.append(future.result())

    # Sort results by pod name for consistent output
    results.sort(key=lambda item: item["pod"])
    return results


def apply_regex_filter(log_text: str, pattern: Optional[str]) -> str:
    """
    Filter log lines by regex pattern if provided.
    """
    if not pattern:
        return log_text

    compiled = re.compile(pattern)
    matched_lines = [line for line in log_text.splitlines() if compiled.search(line)]
    return "\n".join(matched_lines) + ("\n" if matched_lines else "")


def format_aggregated_output(
    results: List[Dict[str, str]],
    grep: Optional[str],
) -> str:
    """
    Convert fetched logs into a readable aggregated string.
    """
    sections = []

    for item in results:
        pod = item["pod"]
        status = item["status"]
        content = item["content"]

        if status == "success":
            content = apply_regex_filter(content, grep)
            if not content.strip():
                content = "[INFO] No matching log lines found.\n"
        else:
            content = f"[ERROR] {content}\n"

        section = (
            f"\n{'=' * 80}\n"
            f"POD: {pod}\n"
            f"STATUS: {status}\n"
            f"{'=' * 80}\n"
            f"{content}"
        )
        sections.append(section)

    return "\n".join(sections)


def write_logs_to_files(
    results: List[Dict[str, str]],
    output_dir: str,
    grep: Optional[str],
) -> None:
    """
    Write each pod's logs to separate files.
    """
    os.makedirs(output_dir, exist_ok=True)

    for item in results:
        pod = item["pod"]
        status = item["status"]
        content = item["content"]

        if status == "success":
            content = apply_regex_filter(content, grep)

        output_path = os.path.join(output_dir, f"{pod}.log")

        with open(output_path, "w", encoding="utf-8") as file_handle:
            if status == "error":
                file_handle.write(f"[ERROR] {content}\n")
            else:
                file_handle.write(content)

        click.echo(f"Wrote logs for pod '{pod}' to: {output_path}")


def write_json_output(results: List[Dict[str, str]], output_file: str, grep: Optional[str]) -> None:
    """
    Write results as structured JSON.
    """
    formatted_results = []

    for item in results:
        content = item["content"]
        if item["status"] == "success":
            content = apply_regex_filter(content, grep)

        formatted_results.append(
            {
                "pod": item["pod"],
                "status": item["status"],
                "logs": content,
            }
        )

    with open(output_file, "w", encoding="utf-8") as file_handle:
        json.dump(formatted_results, file_handle, indent=2)

    click.echo(f"Wrote JSON output to: {output_file}")


@click.command()
@click.option("--namespace", "-n", required=True, help="Kubernetes namespace.")
@click.option("--selector", "-l", required=True, help="Label selector, for example: app=my-service")
@click.option("--container", "-c", required=False, help="Optional container name.")
@click.option("--tail", default=200, show_default=True, type=int, help="Number of log lines to fetch.")
@click.option("--previous", is_flag=True, help="Fetch logs from the previous crashed container instance.")
@click.option("--since", required=False, help="Only return logs newer than a relative duration, e.g. 10m, 1h.")
@click.option("--grep", required=False, help="Regex pattern to filter log lines.")
@click.option("--output-dir", required=False, help="Write each pod's logs to separate files.")
@click.option("--json-output", required=False, help="Write structured output to a JSON file.")
@click.option("--max-workers", default=5, show_default=True, type=int, help="Number of parallel workers.")
def main(
    namespace: str,
    selector: str,
    container: Optional[str],
    tail: int,
    previous: bool,
    since: Optional[str],
    grep: Optional[str],
    output_dir: Optional[str],
    json_output: Optional[str],
    max_workers: int,
) -> None:
    """
    Aggregate Kubernetes pod logs for easier debugging.
    """
    click.echo(f"Looking for pods in namespace '{namespace}' with selector '{selector}'...")
    pods = get_pods(namespace, selector)

    if not pods:
        click.echo("No pods found matching the selector.", err=True)
        sys.exit(1)

    click.echo(f"Found {len(pods)} pod(s): {', '.join(pods)}")

    results = fetch_logs_parallel(
        pods=pods,
        namespace=namespace,
        container=container,
        tail=tail,
        previous=previous,
        since=since,
        max_workers=max_workers,
    )

    if output_dir:
        write_logs_to_files(results, output_dir, grep)

    if json_output:
        write_json_output(results, json_output, grep)

    if not output_dir and not json_output:
        aggregated_output = format_aggregated_output(results, grep)
        click.echo(aggregated_output)


if __name__ == "__main__":
    main()