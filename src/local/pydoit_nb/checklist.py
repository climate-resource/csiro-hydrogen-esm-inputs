"""
Checklist file generation
"""

from pathlib import Path

from doit.dependency import get_file_md5  # type: ignore

_CHECKLIST_FNAME = "checklist.chk"


def get_checklist_file(directory: Path) -> Path:
    """
    Get the filename for a checklist

    Parameters
    ----------
    directory
        Directory containing arbitary data files

    Returns
    -------
        Path of the generated checklist

    """
    return directory / _CHECKLIST_FNAME


def generate_directory_checklist(directory: Path) -> Path:
    """
    Create a file that contains the checksums for all files in a directory

    The checklist is imdepotent, i.e. running this command multiple times
    should result in the same result. This enables the checklist to be used
    as a target for generated outputs.

    The resulting checklist file can also be used to verify the contents
    of a folder using program `mdfsum` so can be included in any distributed
    results.

    .. code:: bash

        md5sum -c checklist.chk

    Parameters
    ----------
    directory
        Directory containing arbitary data files

    Raises
    ------
    NotADirectoryError
        If directory doesn't exist or isn't a directory

    Returns
    -------
        Path of the generated checklist
    """
    if not directory.is_dir():
        raise NotADirectoryError(directory)

    checklist_file = get_checklist_file(directory)

    files = sorted(directory.rglob("*"))

    with open(checklist_file, "w") as fh:
        for f in files:
            # Ignores checklist files recursively
            if f.is_file() and f.stem != _CHECKLIST_FNAME:
                file_md5 = get_file_md5(f)
                # Formatted the same as the results from md5sum
                fh.write(f"MD5 ({f.relative_to(directory)}) = {file_md5}\n")

    return checklist_file
