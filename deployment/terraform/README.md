# Infrastructure Provisioning with Terraform

This directory contains the Terraform configuration to provision the necessary Azure infrastructure for the AFGA application.

## Resources Created

- **Resource Group**: `rg-afga-prod`
- **Azure Container Registry (ACR)**: For storing Docker images.
- **Azure Key Vault**: For managing secrets.
- **AKS Cluster**: Kubernetes cluster with Key Vault CSI Driver enabled.

## Prerequisites

- [Terraform](https://www.terraform.io/downloads.html) installed.
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) installed and logged in (`az login`).

## Usage

1.  **Initialize Terraform:**
    ```bash
    terraform init
    ```

2.  **Review Plan:**
    ```bash
    terraform plan
    ```

3.  **Apply Configuration:**
    ```bash
    terraform apply
    ```
    Type `yes` to confirm.

4.  **Connect to Cluster:**
    After the apply is complete, run the command output by Terraform:
    ```bash
    $(terraform output -raw connect_command)
    ```

## Next Steps

Once the infrastructure is provisioned, proceed to the [Helm Deployment](../helm/README.md) guide to deploy the application.
