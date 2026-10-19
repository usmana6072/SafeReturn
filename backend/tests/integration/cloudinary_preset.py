"""Read/update only the user-selected public media preset; never print credentials."""

from urllib.parse import quote

import httpx
from dotenv import load_dotenv

from app.core.config import Settings


def main():
    load_dotenv(".env")
    s = Settings()
    assert (
        s.cloudinary_cloud_name
        and s.cloudinary_api_key
        and s.cloudinary_api_secret
        and s.cloudinary_upload_preset
    )
    url = f"https://api.cloudinary.com/v1_1/{s.cloudinary_cloud_name}/upload_presets/{quote(s.cloudinary_upload_preset, safe='')}"
    auth = (
        s.cloudinary_api_key.get_secret_value(),
        s.cloudinary_api_secret.get_secret_value(),
    )
    with httpx.Client(auth=auth, timeout=10, follow_redirects=False) as client:
        r = client.get(url)
        print("Preset read HTTP", r.status_code)
        if r.status_code == 404:
            r = client.post(
                url.rsplit("/", 1)[0],
                data={
                    "name": s.cloudinary_upload_preset,
                    "unsigned": "false",
                    "asset_folder": "safereturn/catalog",
                    "overwrite": "false",
                    "allowed_formats": "png,jpg,jpeg,webp,avif",
                    "max_file_size": "5242880",
                    "type": "upload",
                },
            )
            print("Create requested signed public-media preset HTTP", r.status_code)
            if r.status_code not in (200, 201):
                return
            r = client.get(url)
        if r.status_code != 200:
            return
        before = r.json()
        options = before.get("settings", {})
        # Preserve existing options. Only the requested media folder is changed.
        # Dynamic-folder accounts use asset_folder; fixed-folder accounts use folder.
        folder_key = (
            "asset_folder"
            if "asset_folder" in options or not options.get("folder")
            else "folder"
        )
        r = client.put(
            url,
            data={
                **options,
                folder_key: "safereturn/catalog",
                "unsigned": "false",
                "overwrite": "false",
                "allowed_formats": "png,jpg,jpeg,webp,avif",
                "max_file_size": "5242880",
            },
        )
        print("Preset folder update HTTP", r.status_code)
        if r.status_code != 200:
            return
        after = client.get(url)
        assert after.status_code == 200
        config = after.json()
        options = config.get("settings", {})
        print(
            "Folder safereturn/catalog:",
            options.get(folder_key) == "safereturn/catalog",
        )
        print("Signed preset:", config.get("unsigned") is False)
        formats = options.get("allowed_formats", [])
        if isinstance(formats, str):
            formats = formats.split(",")
        print(
            "Raster formats restricted:",
            bool(formats) and set(formats) <= {"png", "jpg", "jpeg", "webp", "avif"},
        )
        print(
            "5 MB maximum configured:", str(options.get("max_file_size")) == "5242880"
        )


if __name__ == "__main__":
    main()
