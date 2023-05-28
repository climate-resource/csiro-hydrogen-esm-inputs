"""
CLI tool for uploading to zenodo
"""
import logging
import os
from functools import partial
from pathlib import Path

import click
from dotenv import load_dotenv
from openscm_zenodo.zenodo import create_new_zenodo_version, get_bucket_id, upload_file
from tqdm.contrib.concurrent import thread_map

DEPOSITION_ID_OLD: str = "7972657"
"""
Deposition ID of our Zenodo archive. This can be any version.
"""

ZENODO_URL: str = "zenodo.org"
"""Zenodo URL to upload to"""

ZENODO_FILE_NAME: str = "zenodo.json"
"""Name of the file in which the Zenodo metadata is written"""


openscm_zenodo_logger = logging.getLogger("openscm_zenodo")
openscm_zenodo_logger.setLevel(logging.INFO)

logFormatter = logging.Formatter(
    "%(levelname)s - %(asctime)s %(name)s %(threadName)s (%(module)s:%(funcName)s:%(lineno)d):  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
stdoutHandler = logging.StreamHandler()
stdoutHandler.setFormatter(logFormatter)

openscm_zenodo_logger.addHandler(stdoutHandler)


@click.command()
@click.argument(
    "bundle_path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True, path_type=Path),
)
def upload_bundle(bundle_path: Path) -> None:
    """
    Upload bundle to zenodo

    Parameters
    ----------
    bundle_path
        Path to bundle
    """
    load_dotenv()

    new_version_deposition_id = create_new_zenodo_version(
        deposition_id=DEPOSITION_ID_OLD,
        zenodo_url=ZENODO_URL,
        token=os.environ["ZENODO_TOKEN"],
        deposit_metadata=bundle_path / ZENODO_FILE_NAME,
    )

    click.echo(f"Deposition ID to use: {new_version_deposition_id}")

    bucket_id = get_bucket_id(
        deposition_id=new_version_deposition_id,
        zenodo_url=ZENODO_URL,
        token=os.environ["ZENODO_TOKEN"],
    )

    click.echo(f"Uploading to bucket: {bucket_id}")

    files_to_upload = []
    for dir_path, _, files in os.walk(bundle_path):
        # Ignore interim outputs
        if "interim" in dir_path:
            continue

        for file in files:
            # Ignore unexecuted notebooks for upload
            if "unexecuted" in file:
                continue

            files_to_upload.append(Path(dir_path) / file)

    click.echo(f"{len(files_to_upload)} files to upload")

    thread_map(
        partial(
            upload_file,
            bucket=bucket_id,
            root_dir=str(bundle_path),
            zenodo_url=ZENODO_URL,
            token=os.environ["ZENODO_TOKEN"],
        ),
        (str(file) for file in files_to_upload),
        desc="File uploads",
        total=len(files_to_upload),
    )


if __name__ == "__main__":
    upload_bundle()
