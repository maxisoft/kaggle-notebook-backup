import argparse
import logging
import pathlib
import shutil
from pathlib import Path

from pathvalidate import FileNameValidator
from sortedcontainers import SortedSet
from tempfile import TemporaryDirectory
from kaggle.api.kaggle_api_extended import KaggleApi
import pathvalidate

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
    kernels = api.kernels_list(
        page=page,
        user=user or api.get_config_value(api.CONFIG_NAME_USER) or api.api_client.configuration.username,
        sort_by="dateRun",
        page_size=page_size,
        mine=True
    )
    if not include_private:
        return [k for k in kernels if not getattr(k, 'isPrivate', getattr(k, 'isPrivateNullable'))]
    else:
        return kernels


def kernel_identity(kernel):
    return getattr(kernel, 'id'), getattr(kernel, 'ref', getattr(kernel, 'title'))


def kernel_to_path(kernel):
    return Path(pathvalidate.sanitize_filename(f"{kernel.ref}#{kernel.id}", replacement_text="_"))


def main(include_private=True, max_page_size=MAX_PAGE_SIZE, user=None, output_name="kernels.zip",
         tmp_dir_prefix="kaggle_", tmp_dir=None):
    parser = argparse.ArgumentParser(description="Download All Kaggle Kernels")
    parser.add_argument(
        "-o", "--output", type=validate_filename, default=output_name,
        help="Name of the output zip file (default: kernels.zip)"
    )
    parser.add_argument(
        "-p", "--include-private", action="store_true", default=include_private,
        help="Include private kernels in the download (default: True)"
    )
    parser.add_argument(
        "-u", "--user", type=str, default=user,
        help="Username of the Kaggle user to search kernels for (default: current user)"
    )
    parser.add_argument(
        "-s", "--max-page-size", type=validate_positive_int, default=max_page_size,
        help="Maximum number of kernels to download per page (default: 100)"
    )
    parser.add_argument(
        "-t", "--tmp-dir", type=str, default=tmp_dir,
        help="Path to the temporary directory (default: None)"
    )

    args = parser.parse_args()

    api = KaggleApi()
    api.authenticate()

    with TemporaryDirectory(prefix=tmp_dir_prefix, dir=args.tmp_dir) as tmpdir:
        kernels = DummyLen(args.max_page_size)
        all_kernels = SortedSet(key=kernel_identity)
        page = 1

        retry_later = SortedSet(key=kernel_identity)

        while len(kernels) >= args.max_page_size:
            kernels = SortedSet(get_kernels(api, args.user, page, bool(args.include_private), args.max_page_size),
                                key=kernel_identity)
            diff = kernels - all_kernels
            if not diff:
                break
            for kernel in diff:
                path = Path(tmpdir, kernel_to_path(kernel))
                try:
                    path.mkdir(parents=True, exist_ok=True)
                    api.kernels_pull(kernel.ref, path=path, metadata=True)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    logging.warning(e, exc_info=True)
                else:
                    all_kernels.add(kernel)

            page += 1

        for kernel in retry_later:
            try:
                path = kernel_to_path(kernel)
                path.mkdir(parents=True, exist_ok=True)
                api.kernels_pull(kernel.ref, path=path, metadata=True)
            except Exception as e:
                logging.warning("Failed to download %r", getattr(kernel, 'ref', getattr(kernel, 'title')),
                                exc_info=True)

        shutil.make_archive(str(Path(args.output).parent / Path(args.output).stem), 'zip', tmpdir)


if __name__ == '__main__':
    main()
