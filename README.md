# FastAPI CI/CD

## Install Minikube on Windows

If `minikube` is not installed, run this in PowerShell:

```powershell
$MinikubeDir = "$env:USERPROFILE\bin"

New-Item -ItemType Directory -Path $MinikubeDir -Force | Out-Null

Invoke-WebRequest `
  -Uri "https://github.com/kubernetes/minikube/releases/latest/download/minikube-windows-amd64.exe" `
  -OutFile "$MinikubeDir\minikube.exe" `
  -UseBasicParsing

$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")

if (($UserPath -split ';') -notcontains $MinikubeDir) {
  [Environment]::SetEnvironmentVariable("Path", "$UserPath;$MinikubeDir", "User")
}

$env:Path += ";$MinikubeDir"

minikube version
```

After installation, open a new PowerShell terminal and start Minikube with Podman:

```powershell
podman version
minikube start --driver=podman --container-runtime=cri-o
minikube kubectl -- get nodes
```

If `cri-o` fails, recreate the cluster with `containerd`:

```powershell
minikube delete
minikube start --driver=podman --container-runtime=containerd
minikube kubectl -- get nodes
```
