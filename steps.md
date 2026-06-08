# FastAPI Production Grade CI/CD Setup (uv + Podman + GHCR + Helm + Kubernetes)

## Architecture

```text
FastAPI
    ↓
GitHub
    ↓
GitHub Actions (CI)
    ↓
Podman Build
    ↓
GHCR (GitHub Container Registry)
    ↓
GitHub Actions (CD)
    ↓
Helm
    ↓
Kubernetes
    ↓
Production
```

---

# Step 0 - Prerequisites

Install:

* Git
* Python 3.12+
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
uv init fastapi-project

cd fastapi-project
```

Install dependencies:

```bash
uv add fastapi
uv add uvicorn

uv add --dev pytest
```

Project structure:

```text
fastapi-project/

├── app/
│   └── main.py

├── tests/

├── pyproject.toml

├── uv.lock

└── README.md
```

---

# Step 2 - Create FastAPI Application

File:

```python
# app/main.py
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def hello():
    return {"message": "Hello Production"}
```

Run locally:

```bash
uv run uvicorn app.main:app --reload
```

Open:

```text
http://localhost:8000
```

---

# Step 3 - Create Dockerfile for Podman

Create:

```dockerfile
# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:latest AS uv


FROM python:3.14-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


FROM python:3.14-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY main.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build image:

```bash
podman build \
-t ghcr.io/ashishpatel26/fastapi-app:v1 .
```

Run image:

```bash
podman run -p 8000:8000 \
ghcr.io/ashishpatel26/fastapi-app:v1
```

---

# Step 4 - Push Image to GHCR

Create GitHub Personal Access Token.

Required permissions:

```text
read:packages
write:packages
```

Login:

```bash
echo <PAT_TOKEN> | podman login ghcr.io \
-u ashishpatel26 \
--password-stdin
```

Push:

```bash
podman push \
ghcr.io/ashishpatel26/fastapi-app:v1
```

Verify package:

```text
https://github.com/ashishpatel26?tab=packages
```

---

# Step 5 - Create Kubernetes Cluster

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

# Step 6 - Install Helm

Create chart:

```bash
helm create fastapi-chart
```

Structure:

```text
fastapi-chart/

├── Chart.yaml

├── values.yaml

└── templates
    ├── deployment.yaml
    ├── service.yaml
    └── ingress.yaml
```

---

# Step 7 - Configure values.yaml

```yaml
image:
  repository: ghcr.io/ashishpatel26/fastapi-app
  tag: v1

replicaCount: 2

service:
  type: ClusterIP
  port: 8000
```

---

# Step 8 - Configure Deployment

File:

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

      containers:

      - name: fastapi

        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"

        ports:
        - containerPort: 8000
```

---

# Step 9 - Deploy Helm Chart

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

# Step 10 - Create GitHub Repository

Repository:

```text
fastapi-production-demo
```

Push code:

```bash
git init

git add .

git commit -m "initial commit"

git branch -M main

git remote add origin \
https://github.com/ashishpatel26/fastapi-production-demo.git

git push -u origin main
```

---

# Step 11 - Create CI Pipeline

File:

```text
.github/workflows/ci.yml
```

Content:

```yaml
name: CI

on:
  push:
    branches:
      - main

jobs:

  test:

    runs-on: ubuntu-latest

    steps:

      - uses: actions/checkout@v4

      - uses: astral-sh/setup-uv@v6

      - run: uv sync --frozen

      - run: uv run pytest

      - run: podman build -t fastapi-app .
```

Pipeline:

```text
Git Push
   ↓
uv sync
   ↓
pytest
   ↓
Podman Build
   ↓
Pass
```

---

# Step 12 - Create CD Pipeline

File:

```text
.github/workflows/cd.yml
```

Content:

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
          echo "${{ secrets.GITHUB_TOKEN }}" | \
          podman login ghcr.io \
          -u ${{ github.actor }} \
          --password-stdin

      - name: Build Image
        run: |
          podman build \
          -t ghcr.io/ashishpatel26/fastapi-app:${{ github.sha }} .

      - name: Push Image
        run: |
          podman push \
          ghcr.io/ashishpatel26/fastapi-app:${{ github.sha }}
```

---

# Step 13 - Deploy New Version

Deploy:

```bash
helm upgrade \
fastapi \
./fastapi-chart \
--set image.tag=<new-tag>
```

Example:

```bash
helm upgrade \
fastapi \
./fastapi-chart \
--set image.tag=7fa91ab
```

---

# Step 14 - Verify Deployment

Check:

```bash
kubectl get pods

kubectl get deployments

kubectl rollout status deployment/fastapi
```

Logs:

```bash
kubectl logs <pod-name>
```

Shell:

```bash
kubectl exec -it <pod-name> -- sh
```

---

# Step 15 - Production Enhancements

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

# Step 16 - GitOps (Recommended)

Modern Flow:

```text
Developer
    ↓
Git Push
    ↓
GitHub Actions
    ↓
Build Image
    ↓
Push to GHCR
    ↓
Update Helm Values
    ↓
GitOps Repo
    ↓
ArgoCD
    ↓
Kubernetes
```

Developer command:

```bash
git add .
git commit -m "new feature"
git push origin main
```

Everything else becomes automatic.

---

# Final Production Stack

```text
FastAPI
 ↓
uv
 ↓
Podman
 ↓
GHCR (ashishpatel26)
 ↓
Helm
 ↓
Kubernetes
 ↓
ArgoCD
 ↓
Prometheus
 ↓
Grafana
 ↓
OpenTelemetry
```
