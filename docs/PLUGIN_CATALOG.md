# Signed plugin packages and catalogs

Flux supports a signed distribution format for plugin metadata and package files. It verifies the publisher's Ed25519 signature and each package file's SHA-256 digest before storing the archive.

**Important:** verification proves that the package matches what the signing key published. It does not prove the plugin is safe. Flux stores package contents as data and does not execute plugin code.

## Publisher setup

Install the optional signing dependency:

```bash
python -m pip install -e ".[plugins]"
```

Generate an Ed25519 key pair. Keep the private key offline or in a secrets manager. The private key file used below contains base64-encoded raw 32-byte key material and must be readable only by its owner on POSIX systems.

```bash
python - <<'PY'
import base64
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

key = Ed25519PrivateKey.generate()
private = key.private_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PrivateFormat.Raw,
    encryption_algorithm=serialization.NoEncryption(),
)
public = key.public_key().public_bytes(
    encoding=serialization.Encoding.Raw,
    format=serialization.PublicFormat.Raw,
)
fd = os.open("plugin-signing.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, "w", encoding="ascii") as handle:
    handle.write(base64.b64encode(private).decode() + "\n")
print("Publish this trusted public key:", base64.b64encode(public).decode())
PY
```

On Windows, restrict the private key file using the account's file ACLs. Never commit or publish the private key.

Create a plugin source directory containing `manifest.json` and its package files. The manifest requires `id`, `name`, and `version`; optional `permissions` must be known Flux permissions.

Build the archive:

```bash
flux plugin-pack ./my-plugin ./dist/my-plugin-1.0.0.fluxplugin --private-key-file ./plugin-signing.key
```

The builder rejects symbolic links, unsafe paths, oversized packages, invalid manifests, and output paths inside the source directory.

## Catalog format

Publish package archives and a JSON catalog over HTTPS. A catalog has this shape:

```json
{
  "schema_version": 1,
  "plugins": [
    {
      "id": "my-plugin",
      "version": "1.0.0",
      "url": "https://plugins.example.org/my-plugin-1.0.0.fluxplugin",
      "sha256": "64-character-lowercase-hex-package-digest"
    }
  ],
  "signature": "base64-ed25519-signature"
}
```

The catalog signature is generated over the JSON object with the `signature` property omitted. Serialize the object using sorted keys, separators `(',', ':')`, UTF-8, and `ensure_ascii=False`. The signature covers the full catalog, including every package URL and digest. Each package independently contains `manifest.json` and `SIGNATURE.ed25519`; its signature covers the validated manifest and SHA-256 digest of every file other than the signature file.

Example catalog-signing script (run by the publisher in a protected environment):

```python
import base64
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

catalog_path = Path("catalog.json")
catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
catalog.pop("signature", None)
private_key = Ed25519PrivateKey.from_private_bytes(
    base64.b64decode(Path("plugin-signing.key").read_text(encoding="ascii").strip())
)
canonical = json.dumps(
    catalog, sort_keys=True, separators=(",", ":"), ensure_ascii=False
).encode()
catalog["signature"] = base64.b64encode(private_key.sign(canonical)).decode()
catalog_path.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
```

Host the signed catalog and archives on a static HTTPS endpoint. Obtain the public key from the publisher through a separate trusted channel. Do not trust a key merely because it is served by the same catalog URL.

## Installation

Install a local package:

```bash
flux plugin-install-package ./my-plugin-1.0.0.fluxplugin --public-key BASE64_TRUSTED_PUBLIC_KEY
```

Install an exact catalog version:

```bash
flux plugin-install my-plugin 1.0.0 --catalog https://plugins.example.org/catalog.json --public-key BASE64_TRUSTED_PUBLIC_KEY
```

Flux rejects HTTP catalog/package URLs, redirects, invalid catalog signatures, duplicate matching entries, digest mismatches, invalid package signatures, unsafe archive paths, and packages that exceed the configured size or file-count limits.

Installed package files are retained as an archive alongside the validated manifest. No package code is imported or run.
