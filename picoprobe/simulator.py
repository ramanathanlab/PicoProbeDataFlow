"""Periodically copies file to a watched directory to simulate a PicoProbe user."""
from argparse import ArgumentParser
from pathlib import Path
import itertools
import shutil
import time


if __name__ == "__main__":
    # Parse user arguments
    parser = ArgumentParser()
    parser.add_argument(
        "-i", "--input", type=Path, required=True, help="Input directory (or file)"
    )
    parser.add_argument(
        "-o", "--output", type=Path, required=True, help="Output directory"
    )
    parser.add_argument(
        "-g", "--glob", type=str, default="*.emd", help="Glob pattern for files to copy"
    )
    parser.add_argument(
        "-t", "--time", type=int, default=10, help="Time between copies (seconds)"
    )
    args = parser.parse_args()

    input_files = list(args.input.glob(args.glob))
    print(f"Copying {len(input_files)} files from {args.input} to {args.output}")

    # Cycle around the input files indefinitely until the program is interrupted
    for ind, file in enumerate(itertools.cycle(input_files)):
        # Copy a unique file name to the output directory
        dst_filename = f"simulator-{ind}-{file.name}"
        dst_file = args.output / dst_filename
        print(f"Copying {file} to {dst_file}")
        shutil.copy(file, dst_file)

        # Sleep between each transfer to simulate the incoming data rate
        time.sleep(args.time)

        # Clean up old data (to avoid running out of storage)
        dst_file.unlink()
