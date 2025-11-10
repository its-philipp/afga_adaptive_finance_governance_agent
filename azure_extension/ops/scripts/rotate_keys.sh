#!/bin/bash
# Rotate secrets in Azure Key Vault

set -e

KEY_VAULT_NAME="${KEY_VAULT_NAME:-}"
SECRET_NAME="${SECRET_NAME:-}"

if [ -z "$KEY_VAULT_NAME" ] || [ -z "$SECRET_NAME" ]; then
    echo "Usage: $0 KEY_VAULT_NAME SECRET_NAME [NEW_VALUE]"
    echo "Example: $0 kv-dev-adaptive-finance-governance openai-api-key"
    exit 1
fi

if [ -n "$3" ]; then
    NEW_VALUE="$3"
else
    echo "Enter new value for secret '${SECRET_NAME}':"
    read -s NEW_VALUE
fi

echo "Rotating secret: ${SECRET_NAME} in ${KEY_VAULT_NAME}"

# Set new secret value
az keyvault secret set \
    --vault-name "${KEY_VAULT_NAME}" \
    --name "${SECRET_NAME}" \
    --value "${NEW_VALUE}"

echo "✅ Secret rotated successfully"

# Note: Restart pods to pick up new secret
echo "⚠️  Restart deployment to pick up new secret:"
echo "   kubectl rollout restart deployment/afga-agent -n afga-agent-dev"

