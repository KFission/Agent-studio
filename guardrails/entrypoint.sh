#!/bin/bash
set -e

MARKER="/app/.validators_installed"

# Install hub validators on first start (non-fatal if it fails)
if [ -n "$GUARDRAILS_TOKEN" ] && [ ! -f "$MARKER" ]; then
    echo "[guardrails] Installing hub validators..."

    # ── SSL bypass for corporate proxy ──────────────────────────────
    # 1. Patch hub_client.py: add verify=False to requests calls
    python3 -c "
import guardrails.cli.server.hub_client as m
p = m.__file__
with open(p) as f: src = f.read()
src = src.replace(
    'req = requests.get(url, headers=headers)',
    'req = requests.get(url, headers=headers, verify=False)'
)
src = src.replace(
    'req = requests.post(submission_url, data=request_body, headers=headers)',
    'req = requests.post(submission_url, data=request_body, headers=headers, verify=False)'
)
with open(p, 'w') as f: f.write(src)
print(f'[guardrails] Patched {p} for SSL bypass')
"

    # 2. Global sitecustomize.py — patches ssl + urllib3 for ALL subprocesses
    #    (needed for spaCy/HuggingFace model downloads during detect_pii install)
    SITE_DIR=$(python3 -c "import site; print(site.getsitepackages()[0])")
    cat > "$SITE_DIR/sitecustomize.py" << 'PYEOF'
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
try:
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass
try:
    import requests
    _orig_send = requests.adapters.HTTPAdapter.send
    def _patched_send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None):
        return _orig_send(self, request, stream=stream, timeout=timeout, verify=False, cert=cert, proxies=proxies)
    requests.adapters.HTTPAdapter.send = _patched_send
except Exception:
    pass
PYEOF
    echo "[guardrails] Installed global SSL bypass (sitecustomize.py)"

    # 3. Trust private PyPI for pip installs
    export PIP_TRUSTED_HOST="pypi.guardrailsai.com pypi.org files.pythonhosted.org"

    # ── Configure hub token ──────────────────────────────────────────
    if [ ! -s /root/.guardrailsrc ]; then
        guardrails configure \
            --enable-metrics \
            --enable-remote-inferencing \
            --token "$GUARDRAILS_TOKEN" || {
            echo "[guardrails] configure failed, writing rc manually"
            python3 -c "import uuid; open('/root/.guardrailsrc','w').write(f'id={uuid.uuid4()}\ntoken=$GUARDRAILS_TOKEN\nenable_metrics=true\nenable_remote_inferencing=true\n')"
        }
    fi

    # ── Install validators ───────────────────────────────────────────
    for v in detect_pii regex_match profanity_free reading_time valid_length; do
        echo "[guardrails] Installing hub://guardrails/$v ..."
        guardrails hub install "hub://guardrails/$v" && echo "[guardrails]   OK: $v" || echo "[guardrails]   SKIP: $v (install failed)"
    done

    # Remove global SSL bypass after install
    rm -f "$SITE_DIR/sitecustomize.py"

    touch "$MARKER"
    echo "[guardrails] Validator install complete."
else
    echo "[guardrails] Validators already installed or no token provided."
fi

echo "[guardrails] Starting guardrails-api server..."
exec uvicorn guardrails_api.app:create_app \
    --factory \
    --workers 1 \
    --host 0.0.0.0 \
    --port 8000 \
    --timeout-keep-alive 30
