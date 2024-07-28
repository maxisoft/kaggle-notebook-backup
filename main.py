import argparse
import json
import logging
import os
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Optional

import pathvalidate
from kaggle.api.kaggle_api_extended import KaggleApi
from sortedcontainers import SortedSet

MAX_PAGE_SIZE = 100


class DummyLen:
    def __init__(self, length):
        self.length = length

    def __len__(self):
        return self.length


def validate_positive_int(value):
    """Validator for positive integer arguments."""
    try:
        val = int(value)
        if val <= 0:
            raise argparse.ArgumentTypeError("Value must be a positive integer.")
        return val
    except ValueError:
        raise argparse.ArgumentTypeError("Value must be a positive integer.")


def validate_filename(value):
    """Validator for filename argument."""

    try:
        p = Path(value)
        p.parent.resolve(strict=True)
        pathvalidate.validate_filename(p.name, platform="auto")
    except (OSError, pathvalidate.ValidationError) as e:
        raise argparse.ArgumentTypeError(f"Invalid filename: {e}")

    return value


def get_kernels(api, user, page=1, include_private=True, page_size=MAX_PAGE_SIZE):
    kernels = api.kernels_list(page=page,
                               user=user or api.get_config_value(api.CONFIG_NAME_USER),
                               sort_by="dateRun", page_size=page_size, mine=True)
    if not include_private:
        yield from (k for k in kernels if not getattr(k, 'isPrivate', getattr(k, 'isPrivateNullable')))
    else:
        yield from kernels


def kernel_identity(kernel):
    return getattr(kernel, 'id'), getattr(kernel, 'ref', getattr(kernel, 'title'))


def kernel_to_path(kernel):
    return Path(pathvalidate.sanitize_filename(f"{kernel.ref}#{kernel.id}", replacement_text="_"))


def fix_kernel_folder(path: Path, remove_private: bool = True) -> Optional[Path]:
    """
    Fixes the name and location of a kernel folder.

    This function takes a path to a kernel folder and performs the following actions:

    1. Checks for the existence of the "kernel-metadata.json" file.
    2. If the file exists, loads the metadata and checks if the kernel is private.
      - If `remove_private` is True and the kernel is private, it removes the entire folder.
      - Otherwise, it sanitizes the kernel name based on its ID and renames the folder if necessary.
    3. Returns the path to the fixed kernel folder or None if the folder was removed.

    Args:
        path (Path): The path to the kernel folder.
        remove_private (bool, optional): Whether to remove private kernels. Defaults to True.

    Returns:
        Optional[Path]: The path to the fixed kernel folder or None if the folder was removed.
    """

    meta_path = Path(path, "kernel-metadata.json")
    if not meta_path.exists():
        logging.warning(f"Kernel metadata not found: {path}")
        return path if not remove_private else None

    with meta_path.open("r") as f:
        metadata = json.load(f)

    if remove_private and metadata.get("is_private", metadata.get("isPrivate", True)):
        logging.debug(f"Removing private kernel: {path}")
        shutil.rmtree(path)
        return None

    new_path = Path(path.parent, pathvalidate.sanitize_filename(
        f"{metadata['id']}#{metadata['id_no']}", replacement_text="_"))

    if new_path != path and not new_path.exists():
        logging.debug(f"Renaming kernel: {path} -> {new_path}")
        shutil.move(path, new_path)
        return new_path

    return path


def main(include_private=False, max_page_size=MAX_PAGE_SIZE, user=None, output_name="kernels.zip",
         tmp_dir_prefix="kaggle_", tmp_dir=None, add_mask=False):
    parser = argparse.ArgumentParser(description="Download All Kaggle Kernels")
    parser.add_argument("-o", "--output", type=validate_filename, default=output_name,
                        help=f"Name of the output zip file (default: {output_name})")
    parser.add_argument("-p", "--include-private", action="store_true", default=include_private,
                        help=f"Include private kernels in the download (default: {include_private})")
    parser.add_argument("-u", "--user", type=str, default=user,
                        help="Username of the Kaggle user to search kernels for (default: current user)")
    parser.add_argument("-s", "--max-page-size", type=validate_positive_int, default=max_page_size,
                        help=f"Maximum number of kernels to download per page (default: {max_page_size})")
    parser.add_argument("-t", "--tmp-dir", type=str, default=tmp_dir,
                        help=f"Path to the temporary directory (default: {tmp_dir})")
    parser.add_argument("--add-mask", action="store_true", default=add_mask,
                        help=argparse.SUPPRESS)

    args = parser.parse_args()
    include_private = bool(args.include_private)
    add_mask = bool(args.add_mask)

    api = KaggleApi()
    api.authenticate()

    with TemporaryDirectory(prefix=tmp_dir_prefix, dir=args.tmp_dir) as tmpdir:
        kernels = DummyLen(args.max_page_size)
        processed_kernels = SortedSet(key=kernel_identity)
        page = 1

        retry_later = SortedSet(key=kernel_identity)

        while len(kernels) >= args.max_page_size:
            kernels = SortedSet(get_kernels(api, args.user, page, include_private, args.max_page_size),
                                key=kernel_identity)
            diff = kernels - processed_kernels
            if not diff:
                break
            for kernel in diff:
                if add_mask:
                    print(f'::add-mask::{kernel.ref}')
                    print(f'::add-mask::{kernel.title}')
                path = Path(tmpdir, kernel_to_path(kernel))
                if add_mask:
                    print(f"::add-mask::{path.name}")
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    api.kernels_pull(kernel.ref, path=path, metadata=True)
                    path = fix_kernel_folder(path, remove_private=not include_private)
                    if add_mask:
                        print(f"::add-mask::{path.name}")
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logging.warning(e, exc_info=True)
                    retry_later.add(kernel)
                finally:
                    processed_kernels.add(kernel)

            page += 1

        for kernel in retry_later:
            try:
                path = Path(tmpdir, kernel_to_path(kernel))
                if add_mask:
                    print(f"::add-mask::{path.name}")
                path.mkdir(parents=True, exist_ok=True)
                api.kernels_pull(kernel.ref, path=path, metadata=True)
                fix_kernel_folder(path, remove_private=not include_private)
            except Exception:  # pylint: disable=broad-except
                logging.warning("Failed to download %r", getattr(kernel, 'ref', getattr(kernel,
                                                                                        'title') if not add_mask else 'hidden kernel name'),
                                exc_info=True)

        shutil.make_archive(str(Path(args.output).parent / Path(args.output).stem), 'zip', tmpdir)


if __name__ == '__main__':
    include_private = os.getenv('KAGGLE_KERNELS_PRIVATE', '').lower() in ('true', '1', 'y', 'yes', 'ok')
    add_mask = os.getenv('KAGGLE_KERNELS_MASK', '').lower() in ('true', '1', 'y', 'yes', 'ok')
    main(include_private=include_private, add_mask=add_mask)
