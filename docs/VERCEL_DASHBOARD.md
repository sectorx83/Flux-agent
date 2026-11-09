# Vercel dashboard and Termux host

Flux is split into two parts:

- **Vercel** serves the static control-room UI and a same-origin API relay.
- **The Flux host** runs Python, Groq requests, workers, integrations, local memory, and Android/Termux actions.

The Vercel deployment is available at:

- https://flux-dashboard-alpha.vercel.app

## Configure the Vercel relay

The Vercel project must have an environment variable named `FLUX_API_URL` containing the public HTTPS origin of the Flux host, with no path or credentials. Example format: `https://flux-host.example.com`.

Set it in Vercel → Project → Settings → Environment Variables for Production (and Preview if needed), then redeploy. Do not put the administrator token or Groq key in Vercel environment variables for this relay.

The relay only forwards the dashboard's supported routes and passes the browser's bearer token to the configured host. It does not store the Flux token.

## Run the host in Termux

Install the core and remote dependencies, then start the API and worker. On Termux, do not install the optional `dev` or `plugins` extras: Ruff and cryptography may lack compatible Android Python 3.14 wheels. The remote extra does not require them:

```bash
pkg update -y && pkg upgrade -y
pkg install python git openssl libffi -y
python -m pip install --upgrade pip
python -m pip install -e ".[remote]"
python -c 'import secrets; print(secrets.token_urlsafe(48))'
export FLUX_REMOTE_TOKEN='paste-the-generated-token'
uvicorn flux_agent.remote.server:create_app --factory --host 127.0.0.1 --port 8765
```

In a second Termux session:

```bash
flux remote-worker
```

Keep the API bound to loopback. Publish it through a trusted HTTPS tunnel or reverse proxy that forwards to `http://127.0.0.1:8765`. Use the tunnel's HTTPS origin as `FLUX_API_URL`. Do not bind the bearer-token API to `0.0.0.0` or expose it directly to the public internet.

## Connect

1. Open the Vercel dashboard URL.
2. Enter the `FLUX_REMOTE_TOKEN` generated on the Termux host.
3. Submit a Chat, Plan, or Build task. Build actions remain subject to host-side approval.
4. Disconnect when finished. The dashboard stores the token only in the current browser tab's session storage.

## Git deployment connection

The initial Vercel deployment was created from the dashboard source files. The Vercel Git integration could not link `sectorx83/Flux-agent` because the connected Vercel GitHub installation currently lacks write/admin access to that repository. To enable automatic deploys on future pushes, grant the Vercel GitHub App access to `sectorx83/Flux-agent` and import/link the repository to the existing `flux-dashboard` Vercel project. The static dashboard is at the repository root.
