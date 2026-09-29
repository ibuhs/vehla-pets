# Vehla Pets

Official downloadable Pet atlases for Vehla.

Pet metadata lives in `pets.json`. Published, immutable WebP atlases are attached
to GitHub Releases, while `catalog.json` and `catalog.sig.json` let Vehla
discover and verify available Pets.

## Publishing

Requirements:

- macOS with Swift and `sips`
- Python 3.10 or newer
- GitHub CLI authenticated for `ibuhs/vehla-pets`
- The Vehla Ed25519 publisher key in `VEHLA_PUBLISHER_PRIVATE_KEY`

Build and sign the catalog from a local atlas directory:

```sh
export VEHLA_PUBLISHER_PRIVATE_KEY="<base64 private key>"
python3 scripts/build-catalog.py \
  --assets-root "/path/to/Vehla/Resources/Pets" \
  --tag "pets-1.0.0"
unset VEHLA_PUBLISHER_PRIVATE_KEY
```

Publish the immutable assets:

```sh
gh release create pets-1.0.0 \
  /path/to/Vehla/Resources/Pets/*/*.webp \
  --repo ibuhs/vehla-pets \
  --title "Vehla Pets 1.0.0" \
  --notes "Initial official Pet collection."
```

Commit `pets.json`, `catalog.json`, and `catalog.sig.json` together. Never
replace an asset in an existing release. Increment that Pet's version and
publish it under a new release tag instead.

## Security

Vehla verifies the detached Ed25519 catalog signature, each atlas SHA-256
checksum, declared byte size, WebP decoding, and the expected 1536×2288 atlas
dimensions before installation.

The signing private key is not stored in this repository.
