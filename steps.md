# FastAPI Production Grade CI/CD Setup (uv + Podman + GHCR + Helm + Kubernetes)

## Architecture

```text
FastAPI
    ↓
GitHub
    ↓
GitHub Actions (CI) — test + build
    ↓
GitHub Actions (CD) — push :sha + :latest to GHCR
    ↓
Helm upgrade
    ↓
Kubernetes (Minikube)
    ↓
Production
```

---

# Step 0 - Prerequisites

Install:

* Git
* Python 3.14+
* uv
* Podman Desktop
* kubectl
* Helm
* Minikube
* VS Code

Verify:

```bash
git --version
python --version
uv --version
podman version
kubectl version --client
helm version
minikube version
```

---

# Step 1 - Create FastAPI Project

```bash
uv init fastapi-ci-cd
cd fastapi-ci-cd
```

Install dependencies:

```bash
uv add fastapi uvicorn
uv add --dev pytest
```

Project structure:

```text
fastapi-ci-cd/
├── main.py
├── tests/
│   └── test_main.py
├── pyproject.toml
└── uv.lock
```

---

# Step 2 - Create FastAPI Application

File `main.py`:

```python
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def hello():
    return {"message": "Hello Production"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {"version": "1.0.0"}
```

Run locally:

```bash
uv run uvicorn main:app --reload
```

Endpoints:

```text
http://localhost:8000/        → {"message": "Hello Production"}
http://localhost:8000/health  → {"status": "ok"}
http://localhost:8000/version → {"version": "1.0.0"}
```

---

# Step 3 - Write Tests

File `tests/test_main.py`:

```python
import importlib.util
import sys
from pathlib import Path

MAIN_PATH = Path(__file__).resolve().parents[1] / "main.py"
SPEC = importlib.util.spec_from_file_location("main", MAIN_PATH)
main = importlib.util.module_from_spec(SPEC)
sys.modules["main"] = main
SPEC.loader.exec_module(main)


def test_hello_returns_production_message():
    assert main.hello() == {"message": "Hello Production"}


def test_health_returns_ok():
    assert main.health() == {"status": "ok"}


def test_version_returns_version():
    assert main.version() == {"version": "1.0.0"}
```

Run:

```bash
uv run pytest -v
```

Expected:

```text
3 passed in 1.02s
```

---

# Step 4 - Create Dockerfile

Uses `ghcr.io/astral-sh/uv:python3.14-bookworm-slim` for both stages — no Docker Hub dependency, no rate limits.

```dockerfile
# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY main.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and test locally:

```bash
podman build -t fastapi-app .
podman run -p 8000:8000 fastapi-app
```

---

# Step 5 - Push Image to GHCR (manual)

Create GitHub Personal Access Token with permissions:

```text
write:packages
read:packages
```

Login:

```bash
echo <PAT_TOKEN> | podman login ghcr.io \
-u ashishpatel26 \
--password-stdin
```

Push:

```bash
podman push ghcr.io/ashishpatel26/fastapi-app:latest
```

Verify:

```text
https://github.com/ashishpatel26?tab=packages
```

---

# Step 6 - Create Kubernetes Cluster

Start Minikube:

```bash
minikube start
```

Verify:

```bash
kubectl get nodes
```

Expected:

```text
NAME       STATUS
minikube   Ready
```

---

# Step 7 - Create GHCR Pull Secret in Kubernetes

Kubernetes needs credentials to pull images from GHCR:

```bash
kubectl create secret docker-registry ghcr-secret \
  --docker-server=ghcr.io \
  --docker-username=ashishpatel26 \
  --docker-password=<PAT_TOKEN> \
  --docker-email=ashishpatel.ce.2011@gmail.com
```

Verify:

```bash
kubectl get secret ghcr-secret
```

---

# Step 8 - Create Helm Chart

```bash
helm create fastapi-chart
```

Structure:

```text
fastapi-chart/
├── Chart.yaml
├── values.yaml
└── templates/
    ├── deployment.yaml
    └── service.yaml
```

---

# Step 9 - Configure values.yaml

```yaml
image:
  repository: ghcr.io/ashishpatel26/fastapi-app
  tag: latest

imagePullSecrets:
  - name: ghcr-secret

replicaCount: 2

service:
  type: ClusterIP
  port: 8000
```

---

# Step 10 - Configure Deployment Template

File `fastapi-chart/templates/deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fastapi
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: fastapi
  template:
    metadata:
      labels:
        app: fastapi
    spec:
      {{- with .Values.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: fastapi
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          ports:
            - containerPort: 8000
```

---

# Step 11 - Deploy Helm Chart

Install:

```bash
helm install fastapi ./fastapi-chart
```

Verify:

```bash
kubectl get pods
kubectl get deployments
kubectl get svc
```

---

# Step 12 - Access the Service

Service type is `ClusterIP` (internal only). Use port-forward to reach it locally:

```bash
kubectl port-forward svc/fastapi-fastapi-chart 8000:8000
```

Then open:

```text
http://localhost:8000
http://localhost:8000/health
http://localhost:8000/version
```

Or switch to NodePort for persistent access:

```bash
# Edit values.yaml: service.type = NodePort
helm upgrade fastapi ./fastapi-chart
minikube service fastapi-fastapi-chart --url
```

---

# Step 13 - Create GitHub Repository

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/ashishpatel26/fastapi-ci-cd.git
git push -u origin main
```

---

# Step 14 - Create CI Pipeline

File `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches:
      - main

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6

      - run: uv sync --frozen

      - run: uv run pytest

      - run: podman build -t fastapi-app .
```

Pipeline flow:

```text
Git Push → uv sync → pytest → podman build → Pass
```

---

# Step 15 - Create CD Pipeline

Add `GHCR_TOKEN` secret to GitHub repo:

```text
GitHub repo → Settings → Secrets and variables → Actions →
New repository secret → Name: GHCR_TOKEN → Value: <PAT with write:packages>
```

File `.github/workflows/cd.yml`:

```yaml
name: CD

on:
  push:
    branches:
      - main

permissions:
  packages: write
  contents: read

jobs:
  build-push:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Login GHCR
        run: |
          echo "${{ secrets.GHCR_TOKEN || secrets.GITHUB_TOKEN }}" | \
          podman login ghcr.io \
          -u ${{ github.actor }} \
          --password-stdin

      - name: Build Image
        run: |
          podman build \
          -t ghcr.io/ashishpatel26/fastapi-app:${{ github.sha }} \
          -t ghcr.io/ashishpatel26/fastapi-app:latest .

      - name: Push Image
        run: |
          podman push ghcr.io/ashishpatel26/fastapi-app:${{ github.sha }}
          podman push ghcr.io/ashishpatel26/fastapi-app:latest
```

Pipeline flow:

```text
Git Push → Login GHCR → Build :sha + :latest → Push both tags → Pass
```

---

# Step 16 - Deploy New Version After Pipeline

After CD passes, upgrade Helm to pull the latest image:

```bash
helm upgrade fastapi ./fastapi-chart
```

Or pin to a specific commit SHA:

```bash
helm upgrade fastapi ./fastapi-chart \
  --set image.tag=<github-sha>
```

Verify rollout:

```bash
kubectl get pods
kubectl rollout status deployment/fastapi
kubectl logs <pod-name>
```

---

# Step 17 - Full End-to-End Flow

```text
Developer: git push origin main
              ↓
CI: uv sync → pytest (3 passed) → podman build
              ↓
CD: podman login ghcr.io → build :sha + :latest → push to GHCR
              ↓
Local: helm upgrade fastapi ./fastapi-chart
              ↓
Kubernetes: pulls ghcr.io/ashishpatel26/fastapi-app:latest using ghcr-secret
              ↓
kubectl port-forward svc/fastapi-fastapi-chart 8000:8000
              ↓
http://localhost:8000/health → {"status": "ok"}
```

---

# Step 18 - Production Enhancements

## Secrets

```text
GitHub Secrets
Kubernetes Secrets
Hashicorp Vault
```

## Monitoring

```text
Prometheus
Grafana
```

## Logging

```text
OpenSearch
ELK
```

## Autoscaling

```text
Horizontal Pod Autoscaler (HPA)
```

## Security

```text
Trivy
Dependabot
Image Scanning
```

---

# Step 19 - GitOps (Recommended)

Modern flow:

```text
Developer
    ↓
Git Push
    ↓
GitHub Actions
    ↓
Build Image
    ↓
Push to GHCR (:sha + :latest)
    ↓
Update Helm Values
    ↓
GitOps Repo
    ↓
ArgoCD
    ↓
Kubernetes
```

Developer only runs:

```bash
git add .
git commit -m "new feature"
git push origin main
```

Everything else automatic.

---

# Final Production Stack

```text
FastAPI (3 endpoints)
 ↓
uv (dependency management)
 ↓
Podman (container build)
 ↓
GHCR (ghcr.io/ashishpatel26/fastapi-app)
 ↓
Helm (fastapi-chart)
 ↓
Kubernetes / Minikube
 ↓
ArgoCD (GitOps)
 ↓
Prometheus + Grafana
 ↓
OpenTelemetry
```
