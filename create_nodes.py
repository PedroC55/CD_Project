import argparse
import requests
import tempfile
from pathlib import Path
from zipfile import ZipFile

ALL_IMAGES_URL = "https://filesender.fccn.pt/download.php?token=675d4815-86ba-45da-b58d-d8be6c33ecc4&files_ids=24396"
ALL_IMAGES_FILE = "all_images.zip"
IMAGE_EXTENSION = (".png", ".jpg", ".jpeg")


def create_files(folders, files):
    zip_file = Path(ALL_IMAGES_FILE)
    if not zip_file.is_file():
        with open(ALL_IMAGES_FILE, "wb") as file:
            print(f"Please wait, while downloading the zipfile from {ALL_IMAGES_URL}")
            res = requests.get(ALL_IMAGES_URL)
            file.write(res.content)

    with ZipFile(ALL_IMAGES_FILE) as images_zip:
        with tempfile.TemporaryDirectory() as tmpdirname:
            print("created temporary directory", tmpdirname)

            images_zip.extractall(
                path=tmpdirname,
                members=[
                    image
                    for image in images_zip.namelist()
                    if image.startswith("images")
                ],
            )
            all_images = iter(
                sorted(
                    [
                        file
                        for file in Path(tmpdirname).rglob("*")
                        if file.is_file()
                        and file.suffix.lower() in IMAGE_EXTENSION
                    ]
                )
            )

            for node in range(folders):
                nodedir = Path(f"node{node}")
                if nodedir.is_dir():
                    # Remove all files
                    for image_file in nodedir.rglob("*"):
                        if image_file.is_file():
                            image_file.unlink()
                else:
                    nodedir.mkdir(parents=True, exist_ok=True)

                for _ in range(files):
                    image_file = next(all_images)
                    print(f"node{node}", image_file)
                    if image_file.is_file():
                        Path(image_file).rename(nodedir / image_file.name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "folders", help="number of folders to create", type=int, default=3
    )
    parser.add_argument(
        "-f", "--files", help="number of files to distribute", type=int, default=10
    )
    args = parser.parse_args()

    create_files(args.folders, args.files)