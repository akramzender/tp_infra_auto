#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Kubernetes Profile Generator - G6
Generates Docker images and Helm charts from profile definitions
"""

import yaml
import os
import sys

# Force UTF-8 encoding for all file operations
if sys.version_info >= (3, 0):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


def load_profile(path="profile.yaml"):
    """Load and parse the profile YAML file"""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_dockerfile(profile):
    """Generate Dockerfile from profile specification"""
    distro = profile["os"]["distro"]
    version = profile["os"]["version"]
    packages = profile["packages"]

    base_image = f"{distro}:{version}"
    pkg_list = " ".join(packages)

    dockerfile = f"""FROM {base_image}

RUN apt-get update && \\
    apt-get install -y {pkg_list} && \\
    rm -rf /var/lib/apt/lists/*

CMD ["/bin/sh", "-c", "while true; do sleep 3600; done"]
"""
    
    os.makedirs("generated", exist_ok=True)
    with open("generated/Dockerfile", "w", encoding="utf-8") as f:
        f.write(dockerfile)
    
    print("[OK] Dockerfile generated -> generated/Dockerfile")


def generate_helm(profile):
    """Generate complete Helm chart from profile"""
    name = profile["profile"]["name"]
    distro = profile["os"]["distro"]
    version = profile["os"]["version"]
    prof_ver = profile["profile"]["version"]

    # Image tag: os-name-version
    image_tag = f"{distro}-{name}-v{prof_ver}"

    # Create chart directories
    os.makedirs("generated/helm/templates", exist_ok=True)

    # Chart.yaml
    chart_yaml = f"""apiVersion: v2
name: {name}
description: Auto-generated chart for profile {name}
type: application
version: "{prof_ver}"
appVersion: "{prof_ver}"
"""
    with open("generated/helm/Chart.yaml", "w", encoding="utf-8") as f:
        f.write(chart_yaml)
    print("[OK] Chart.yaml generated")

    # values.yaml
    values_yaml = f"""replicaCount: 1

image:
  repository: YOUR_DOCKERHUB_USERNAME/{name}
  tag: "{image_tag}"
  pullPolicy: IfNotPresent

namespace: {name}

service:
  type: ClusterIP
  port: 80

app:
  name: {name}
"""
    with open("generated/helm/values.yaml", "w", encoding="utf-8") as f:
        f.write(values_yaml)
    print("[OK] values.yaml generated")

    # templates/namespace.yaml
    namespace_yaml = f"""apiVersion: v1
kind: Namespace
metadata:
  name: {name}
"""
    with open("generated/helm/templates/namespace.yaml", "w", encoding="utf-8") as f:
        f.write(namespace_yaml)
    print("[OK] namespace.yaml generated")

    # templates/deployment.yaml
    deployment_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .Values.app.name }}
  namespace: {{ .Values.namespace }}
  labels:
    app: {{ .Values.app.name }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ .Values.app.name }}
  template:
    metadata:
      labels:
        app: {{ .Values.app.name }}
    spec:
      containers:
        - name: {{ .Values.app.name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          ports:
            - containerPort: 80
          command: ["/bin/sh", "-c", "while true; do sleep 3600; done"]
"""
    with open("generated/helm/templates/deployment.yaml", "w", encoding="utf-8") as f:
        f.write(deployment_yaml)
    print("[OK] deployment.yaml generated")

    # templates/service.yaml
    service_yaml = """apiVersion: v1
kind: Service
metadata:
  name: {{ .Values.app.name }}-svc
  namespace: {{ .Values.namespace }}
spec:
  selector:
    app: {{ .Values.app.name }}
  ports:
    - protocol: TCP
      port: {{ .Values.service.port }}
      targetPort: 80
  type: {{ .Values.service.type }}
"""
    with open("generated/helm/templates/service.yaml", "w", encoding="utf-8") as f:
        f.write(service_yaml)
    print("[OK] service.yaml generated")

    # templates/networkpolicy.yaml
    generate_network_policies(profile, name)


def generate_network_policies(profile, name):
    """Generate NetworkPolicy manifests from profile rules"""
    network = profile["network"]
    rules = network.get("rules", [])

    ingress_rules = [r for r in rules if r["direction"] == "ingress"]
    egress_rules = [r for r in rules if r["direction"] == "egress"]

    # Build ingress block
    ingress_block = ""
    if ingress_rules:
        ingress_block = "  ingress:\n"
        for rule in ingress_rules:
            ns = rule.get("from", {}).get("namespace", "")
            ingress_block += f"""  - from:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {ns}
    ports:
    - protocol: {rule["protocol"]}
      port: {rule["port"]}
"""
    else:
        ingress_block = "  ingress: []\n"

    # Build egress block
    egress_block = ""
    if egress_rules:
        egress_block = "  egress:\n"
        for rule in egress_rules:
            ns = rule.get("to", {}).get("namespace", "")
            egress_block += f"""  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: {ns}
    ports:
    - protocol: {rule["protocol"]}
      port: {rule["port"]}
"""
    else:
        egress_block = "  egress: []\n"

    # Determine policyTypes
    policy_types = []
    if network.get("default_deny_ingress"):
        policy_types.append("Ingress")
    if network.get("default_deny_egress"):
        policy_types.append("Egress")
    policy_types_str = "\n".join([f"  - {pt}" for pt in policy_types])

    networkpolicy_yaml = f"""# Policy 1: Default Deny
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny
  namespace: {{{{ .Values.namespace }}}}
spec:
  podSelector: {{}}
  policyTypes:
{policy_types_str}
---
# Policy 2: Allow exceptions
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {{{{ .Values.app.name }}}}-allow
  namespace: {{{{ .Values.namespace }}}}
spec:
  podSelector:
    matchLabels:
      app: {{{{ .Values.app.name }}}}
  policyTypes:
{policy_types_str}
{ingress_block}{egress_block}"""

    with open("generated/helm/templates/networkpolicy.yaml", "w", encoding="utf-8") as f:
        f.write(networkpolicy_yaml)
    print("[OK] networkpolicy.yaml generated")


def main():
    """Main entry point"""
    profile_path = sys.argv[1] if len(sys.argv) > 1 else "profile.yaml"
    
    print("\n=== Kubernetes Profile Generator ===")
    print(f"Reading profile: {profile_path}\n")

    profile = load_profile(profile_path)

    generate_dockerfile(profile)
    generate_helm(profile)

    print("\n=== Generation Complete ===")
    print("All files generated in generated/ directory")
    print("\nNext steps:")
    print("  1. Update values.yaml with your Docker Hub username")
    print("  2. Run: docker build -t <username>/<image>:<tag> -f generated/Dockerfile .")
    print("  3. Run: docker push <username>/<image>:<tag>")
    print("  4. Run: helm install <name> generated/helm --namespace <namespace> --create-namespace")
    print()


if __name__ == "__main__":
    main()
