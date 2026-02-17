#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Complete Automated Deployment Script - G6 Project
Generates files, builds image, and deploys to Kubernetes
"""

import subprocess
import sys
import os
import time
import yaml


def print_header(message):
    print(f"\n{'='*60}")
    print(f" {message}")
    print(f"{'='*60}\n")


def print_step(step_num, message):
    print(f"\n>> STEP {step_num}: {message}")


def print_success(message):
    print(f"[OK] {message}")


def print_info(message):
    print(f"[INFO] {message}")


def print_error(message):
    print(f"[ERROR] {message}")
    sys.exit(1)


def run_command(command, check=True):
    """Run a shell command"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        if result.stdout:
            print(result.stdout.strip())
        return result.returncode == 0, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"Command failed: {command}")
        return False, ""


def check_prerequisites():
    """Check if all tools are installed"""
    print_step(0, "Checking Prerequisites")
    
    tools = [
        ("Docker", "docker --version"),
        ("kubectl", "kubectl version --client"),
        ("Helm", "helm version --short"),
        ("Minikube", "minikube version --short"),
        ("Python", "python --version")
    ]
    
    for tool, cmd in tools:
        success, _ = run_command(cmd, check=False)
        if success:
            print_success(f"{tool} found")
        else:
            print_error(f"{tool} not found. Please install {tool}.")
    
    # Check Docker daemon
    success, _ = run_command("docker info", check=False)
    if success:
        print_success("Docker daemon is running")
    else:
        print_error("Docker daemon not running. Start Docker Desktop.")


def get_docker_username():
    """Get Docker Hub username from user"""
    print_step(1, "Docker Hub Configuration")
    username = input("Enter your Docker Hub username: ").strip()
    if not username:
        print_error("Username cannot be empty")
    print_success(f"Docker Hub username: {username}")
    return username


def generate_files():
    """Generate Dockerfile and Helm charts"""
    print_step(2, "Generating Files from Profile")
    
    if not os.path.exists("profile.yaml"):
        print_error("profile.yaml not found in current directory")
    
    if not os.path.exists("generate.py"):
        print_error("generate.py not found in current directory")
    
    print_info("Running: python generate.py profile.yaml")
    success, _ = run_command("python generate.py profile.yaml")
    
    if not success:
        print_error("File generation failed")
    
    print_success("All files generated in generated/ directory")


def update_values_yaml(username):
    """Update values.yaml with Docker Hub username"""
    print_step(3, "Updating values.yaml with Docker Hub Username")
    
    values_path = "generated/helm/values.yaml"
    
    if not os.path.exists(values_path):
        print_error(f"File not found: {values_path}")
    
    # Read
    with open(values_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Replace
    content = content.replace("YOUR_DOCKERHUB_USERNAME", username)
    
    # Write
    with open(values_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    print_success("values.yaml updated")
    
    # Parse to get info
    with open(values_path, "r", encoding="utf-8") as f:
        values = yaml.safe_load(f)
    
    return {
        'image_full': f"{values['image']['repository']}:{values['image']['tag']}",
        'app_name': values['app']['name'],
        'namespace': values['namespace']
    }


def start_minikube():
    """Start Minikube if not running"""
    print_step(4, "Starting Minikube")
    
    success, status = run_command("minikube status", check=False)
    
    if success and "Running" in status:
        print_success("Minikube already running")
    else:
        print_info("Starting Minikube (may take a few minutes)...")
        run_command("minikube start --driver=docker")
        print_success("Minikube started")
    
    # Verify cluster
    success, _ = run_command("kubectl get nodes", check=False)
    if success:
        print_success("Kubernetes cluster ready")


def build_image(image_full):
    """Build Docker image"""
    print_step(5, "Building Docker Image")
    
    print_info(f"Building: {image_full}")
    run_command(f"docker build -t {image_full} -f generated\\Dockerfile .")
    print_success("Image built successfully")


def push_image(image_full):
    """Push image to Docker Hub"""
    print_step(6, "Pushing Image to Docker Hub")
    
    # Check if logged in
    success, info = run_command("docker info", check=False)
    if not success or "Username:" not in info:
        print_info("Logging in to Docker Hub...")
        os.system("docker login")
    
    print_info(f"Pushing: {image_full}")
    run_command(f"docker push {image_full}")
    print_success("Image pushed to Docker Hub")


def deploy_helm(app_name, namespace):
    """Deploy with Helm"""
    print_step(7, "Deploying to Kubernetes with Helm")
    
    # Cleanup existing
    print_info("Cleaning up existing deployment...")
    run_command(f"helm uninstall {app_name} --namespace {namespace}", check=False)
    run_command(f"kubectl delete namespace {namespace}", check=False)
    time.sleep(3)
    
    # Install
    print_info(f"Installing {app_name}...")
    run_command(f"helm install {app_name} generated\\helm --namespace {namespace} --create-namespace")
    print_success("Helm chart installed")
    
    # Wait for pod
    print_info("Waiting for pod to be ready...")
    time.sleep(10)
    run_command(f"kubectl wait --for=condition=ready pod -l app={app_name} -n {namespace} --timeout=120s", check=False)
    print_success("Pod is ready")


def verify_deployment(app_name, namespace):
    """Verify the deployment"""
    print_step(8, "Verifying Deployment")
    
    print_info(f"\nResources in namespace '{namespace}':")
    run_command(f"kubectl get all -n {namespace}", check=False)
    
    print_info(f"\nNetworkPolicies:")
    run_command(f"kubectl get networkpolicy -n {namespace}", check=False)


def main():
    """Main function"""
    print_header("PROJET G6 - COMPLETE AUTOMATED DEPLOYMENT")
    
    print_info("This script will:")
    print_info("  1. Generate Dockerfile and Helm charts from profile.yaml")
    print_info("  2. Build Docker image")
    print_info("  3. Push to Docker Hub")
    print_info("  4. Deploy to Kubernetes with Helm")
    print_info("  5. Verify deployment\n")
    
    # Check prerequisites
    check_prerequisites()
    
    # Get Docker Hub username
    username = get_docker_username()
    
    # Generate files from profile
    generate_files()
    
    # Update values.yaml
    info = update_values_yaml(username)
    
    print_info(f"\nDeployment Info:")
    print_info(f"  Image: {info['image_full']}")
    print_info(f"  Namespace: {info['namespace']}")
    
    # Confirm
    confirm = input("\nProceed with deployment? [Y/n]: ").strip().lower()
    if confirm and confirm != 'y':
        print_info("Deployment cancelled")
        sys.exit(0)
    
    # Execute deployment
    start_minikube()
    build_image(info['image_full'])
    push_image(info['image_full'])
    deploy_helm(info['app_name'], info['namespace'])
    verify_deployment(info['app_name'], info['namespace'])
    
    # Success
    print_header("DEPLOYMENT COMPLETE!")
    
    print(f"""
Next steps:
-----------
Verify deployment:
  kubectl get all -n {info['namespace']}
  kubectl get networkpolicy -n {info['namespace']}

View logs:
  kubectl logs -l app={info['app_name']} -n {info['namespace']}

Cleanup:
  helm uninstall {info['app_name']} --namespace {info['namespace']}
  kubectl delete namespace {info['namespace']}

Docker Hub:
  https://hub.docker.com/r/{username}/{info['app_name']}
""")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nDeployment interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {str(e)}")
