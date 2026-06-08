# Deploy After CD Pipeline

## Flow

```
git push origin main
        │
        └──► CI: test + build
        └──► CD: build + push :sha + :latest → ghcr.io/ashishpatel26/fastapi-app
                        │
                        ▼
             helm upgrade → k8s pulls :latest using ghcr-secret
                        │
                        ▼
             kubectl port-forward → http://localhost:8000
```

---

## Commands

```bash
# 1. Upgrade Helm (pulls latest image from GHCR)
helm upgrade fastapi ./fastapi-chart

# 2. Verify pods are running with new image
kubectl get pods
kubectl describe pod <pod-name> | grep Image

# 3. Access locally
kubectl port-forward svc/fastapi-fastapi-chart 8000:8000
```

Open:

```text
http://localhost:8000           → {"message": "Hello Production"}
http://localhost:8000/health    → {"status": "ok"}
http://localhost:8000/version   → {"version": "1.0.0"}
http://localhost:8000/docs      → Swagger UI
```
