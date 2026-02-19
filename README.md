# PROJET G6 - Generateur Automatique

## Contenu

```
projet-g6/
├── profile.yaml                    # Profil d'entree (Ubuntu + curl/jq/git)
├── generate.py                     # Generateur de fichiers
├── deploy.py                       # Script de deploiement automatique
├── requirements.txt                # Dependances Python
├── Projet_G6_Presentation.pptx     # Presentation (9 slides)
└── Discours_Presentation_G6.docx   # Discours (3 personnes x 5 min)
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Deploiement Automatique en 1 Commande

```bash
python deploy.py
```

Le script va :
1. ✅ Verifier les outils (Docker, kubectl, Helm, Minikube)
2. ✅ Te demander ton username Docker Hub
3. ✅ Generer tous les fichiers (Dockerfile + Helm charts)
4. ✅ Demarrer Minikube
5. ✅ Builder l'image Docker
6. ✅ Pusher sur Docker Hub
7. ✅ Deployer avec Helm
8. ✅ Verifier le deploiement


---

## Exemple de Session

```
>> STEP 1: Docker Hub Configuration
Enter your Docker Hub username: akramzender
[OK] Docker Hub username: akramzender

>> STEP 2: Generating Files from Profile
[INFO] Running: python generate.py profile.yaml
[OK] Dockerfile generated -> generated/Dockerfile
[OK] Chart.yaml generated
[OK] values.yaml generated
...

>> STEP 3: Updating values.yaml with Docker Hub Username
[OK] values.yaml updated

Deployment Info:
  Image: akramzender/debug-ubuntu:ubuntu-debug-ubuntu-v1.0
  Namespace: debug-ubuntu

Proceed with deployment? [Y/n]: y

>> STEP 4: Starting Minikube
[OK] Minikube already running

>> STEP 5: Building Docker Image
[INFO] Building: akramzender/debug-ubuntu:ubuntu-debug-ubuntu-v1.0
...
```

---

## Deploiement Manuel (Si tu preferes)

```bash
# 1. Generer les fichiers
python generate.py profile.yaml

# 2. Editer generated/helm/values.yaml
# Remplacer YOUR_DOCKERHUB_USERNAME par ton username

# 3. Demarrer Minikube
minikube start --driver=docker

# 4. Builder l'image
docker build -t username/debug-ubuntu:ubuntu-debug-ubuntu-v1.0 -f generated/Dockerfile .

# 5. Pusher sur Docker Hub
docker login
docker push username/debug-ubuntu:ubuntu-debug-ubuntu-v1.0

# 6. Deployer
helm install debug-ubuntu generated/helm --namespace debug-ubuntu --create-namespace

# 7. Verifier
kubectl get all -n debug-ubuntu
kubectl get networkpolicy -n debug-ubuntu
```

---

## Verification

```bash
kubectl get all -n debug-ubuntu
kubectl get networkpolicy -n debug-ubuntu
kubectl describe pod -l app=debug-ubuntu -n debug-ubuntu
kubectl logs -l app=debug-ubuntu -n debug-ubuntu
```

---

## Nettoyage

```bash
helm uninstall debug-ubuntu --namespace debug-ubuntu
kubectl delete namespace debug-ubuntu
minikube stop
```

---

## Pour la Demo

```bash
python deploy.py
```

Entrer ton username Docker Hub, attendre 2-3 minutes, puis montrer les ressources deployees !

---

## Ce qui est deploye

- **Image Docker** : Ubuntu 22.04 + curl + jq + git
- **Namespace** : debug-ubuntu
- **Deployment** : 1 replica
- **Service** : ClusterIP port 80
- **NetworkPolicies** :
  - Default deny (tout bloque)
  - TCP/80 ingress autorise
  - UDP/53 egress autorise (DNS)
