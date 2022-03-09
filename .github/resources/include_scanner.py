"""
"""

import click
import json
import re
import yaml

from os import walk
from os.path import isfile, join


ORIGIN = "https://raw.githubusercontent.com/jobtome-labs/ci-templates/"

DIRECTORY_PATH = "."

CURRENT_VERSION_NUMBER = None

TAG_REGEX_PATTERN = r"^v\d+\.\d+\.\d+$"
TAG_REGEX_PATTERN_GROUPS = r"^v(\d+)\.(\d+)\.(\d+)$"


def _convert_version_to_number(version):
    """
    """

    groups = re.findall(TAG_REGEX_PATTERN_GROUPS, version)

    if not groups:
        return None

    groups = list(groups[0])

    version_number = 0

    for index in range(len(groups)):

        version_number += int(groups[-index - 1]) * (10 ** index)

    return version_number


def _get_yaml_file_paths(directory_path="."):
    """
    """

    file_paths = []

    for root, directories, files in walk(directory_path):

        for file in files:

            if file.endswith(".yaml") or file.endswith(".yml"):

                file_paths.append(join(root, file))

    return file_paths


def _extract_git_revision(remote_template_link):
    """
    """

    revision = []

    template_file_path = remote_template_link.split(ORIGIN)[-1]

    while True:

        parts = template_file_path.split("/", 1)

        revision.append(parts[0])
        template_file_path = parts[-1]

        if isfile(template_file_path):
            break

        if "/" not in template_file_path:
            break

    return "/".join(revision)


def validate(remote_template_link, verbose, test_results):
    """
    """

    if remote_template_link.startswith(ORIGIN):

        test_results["passed"].append("ORIGIN")

    else:

        test_results["failed"].append("ORIGIN")

    revision = _extract_git_revision(remote_template_link)

    click.echo(
        f" --- Next Version Number (Detected): \"{revision}\".") if verbose >= 2 else None

    if re.match(TAG_REGEX_PATTERN, revision):

        test_results["passed"].append("TAG_REGEX_PATTERN")

        next_version_number = _convert_version_to_number(revision)

        if next_version_number is not None:

            click.echo(
                f" --- Next Version Number (Converted): \"{next_version_number}\".") if verbose >= 2 else None

            if next_version_number > CURRENT_VERSION_NUMBER:

                test_results["passed"].append("NEXT_VERSION")

            else:

                test_results["failed"].append("NEXT_VERSION")

        else:

            test_results["failed"].append("TAG_REGEX_PATTERN")

    else:

        test_results["failed"].append("TAG_REGEX_PATTERN")

    return test_results


def scan_templates(ci_template_file_paths, verbose):
    """
    """

    results = {}

    for template_file_path in ci_template_file_paths:

        click.echo(
            f" === Analyzing CI-Template: \"{template_file_path}\" ..\n") if verbose else None

        results[template_file_path] = {
            "passed": [],
            "failed": []
        }

        try:

            with open(template_file_path, "r", encoding="utf-8") as f:
                template = yaml.safe_load(f)

            results[template_file_path]["passed"].append("YAML")

        except yaml.YAMLError as e:

            results[template_file_path]["failed"].append("YAML")

            continue

        click.echo(
            " === YAML File Loaded Successfully.") if verbose >= 2 else None

        if "include" in template:

            remote_template_links = [
                remote_template["remote"] for remote_template in template["include"]]

            remote_template_links_count = len(remote_template_links)

            click.echo(
                f" === Found {remote_template_links_count} Remote Template Links.") if verbose >= 2 else None

            click.echo("") if verbose >= 2 else None

            index = 1

            for remote_template_link in remote_template_links:

                click.echo(
                    f" --- [{index}/{remote_template_links_count}] Validating Remote Template Link: \"{remote_template_link}\" ..") if verbose else None

                results[template_file_path]["remote-template-links"] = {}

                results[template_file_path]["remote-template-links"][remote_template_link] = {
                    "passed": [],
                    "failed": []
                }

                test_results = validate(
                    remote_template_link,
                    verbose,
                    results[template_file_path]["remote-template-links"][remote_template_link]
                )

                click.echo(
                    f" --- Test Results: {len(test_results['passed'])} Passed and {len(test_results['failed'])} Failed Test Checks: {results[template_file_path]['remote-template-links'][remote_template_link]}.") if verbose else None

                click.echo(
                    f" --- [{index}/{remote_template_links_count}] Done.\n") if verbose else None

                index += 1

        else:

            click.echo(
                " === No Include Statements Found.\n") if verbose >= 2 else None

        click.echo(" === Done.\n") if verbose else None

    return results


def filter_failed(results):
    """
    """

    results_failed = {}

    failures = 0

    for template_file_path in results.keys():

        if results[template_file_path]["failed"]:

            results_failed[template_file_path] = {}
            results_failed[template_file_path]["failed"] = results[template_file_path]["failed"]

            failures += 1

        if "remote-template-links" in results[template_file_path]:

            for remote_template_link in results[template_file_path]["remote-template-links"].keys():

                if results[template_file_path]["remote-template-links"][remote_template_link]["failed"]:

                    if template_file_path not in results_failed:
                        results_failed[template_file_path] = {}

                    if "remote-template-links" not in results_failed[template_file_path]:
                        results_failed[template_file_path]["remote-template-links"] = {}

                    results_failed[template_file_path]["remote-template-links"][remote_template_link] = {}
                    results_failed[template_file_path]["remote-template-links"][remote_template_link]["failed"] = \
                        results[template_file_path]["remote-template-links"][remote_template_link]["failed"]

                    failures += 1

    return results_failed, failures


@click.group()
def cli():
    """
    """


@click.command()
@click.option(
    "-o",
    "--origin",
    type=str,
    required=False,
    default=ORIGIN,
    help="The Git Repository Origin.")
@click.option(
    "-t",
    "--current-tag",
    type=str,
    required=True,
    help="The Current Latest Git Tag.")
@click.option(
    "-v",
    "--verbose",
    count=True,
    help="Verbose (can be supplied multiple times to increase verbosity).")
@click.argument(
    "directory-path",
    default=DIRECTORY_PATH,
    type=click.Path(exists=True, file_okay=False, dir_okay=True, writable=False, readable=True, resolve_path=True, allow_dash=False, path_type=None))
def scan(origin, current_tag, verbose, directory_path):
    """
    Scan and Validate Include Statements of CI-Templates.
    """

    click.echo("")

    click.echo(
        " ^^^ Scanning and Validating Include Statements of CI-Templates ..\n")

    click.echo(" *** [1/4] Validating Inputs ..")

    global ORIGIN
    ORIGIN = origin

    global DIRECTORY_PATH
    DIRECTORY_PATH = directory_path

    global CURRENT_VERSION_NUMBER

    current_version_number = _convert_version_to_number(current_tag)

    if current_version_number is None:

        click.echo(
            f" ERROR: Invalid Value for CURRENT TAG Parameter: \"{current_tag}\".", err=True)
        click.echo(
            f" ERROR: The CURRENT TAG Parameter should match the Regular Expression: \"{TAG_REGEX_PATTERN_GROUPS}\".",
            err=True)

        click.echo("", err=True)

        exit(code=1)

    CURRENT_VERSION_NUMBER = current_version_number

    click.echo(
        f" *** Current Version Number (Converted): \"{CURRENT_VERSION_NUMBER}\".") if verbose >= 2 else None

    click.echo(" *** [1/4] Done.\n")

    click.echo(" *** [2/4] Looking for YAML CI-Templates ..")

    yaml_file_paths = _get_yaml_file_paths(directory_path)

    click.echo(
        f" *** Found {len(yaml_file_paths)} YAML CI-Templates.") if verbose >= 2 else None

    click.echo(" *** [2/4] Done.\n")

    click.echo(" *** [3/4] Scanning and Validating Include Statements ..")

    click.echo("") if verbose >= 1 else None

    results = scan_templates(yaml_file_paths, verbose)

    click.echo(" *** [3/4] Done.\n")

    click.echo(" *** [4/4] Printing Results ..")

    click.echo("")

    click.echo(
        f" *** All Results: {json.dumps(results, indent=True)}\n") if verbose >= 2 else None

    results_failed, failures = filter_failed(results)

    click.echo(
        f" *** Failed Results ({failures}): {json.dumps(results_failed, indent=True)}\n")

    click.echo(" *** [4/4] Done.\n")

    click.echo(" ^^^ Done.")

    click.echo("")

    if results_failed:
        exit(code=9)


if __name__ == "__main__":
    """
    """

    cli.add_command(scan)

    cli()
