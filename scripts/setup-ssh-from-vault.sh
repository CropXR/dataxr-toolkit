#!/bin/bash
# setup-ssh-from-vault.sh - SSH configuration setup with HashiCorp Vault

set -e

# Display usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

SSH setup script that reads connection details from HashiCorp Vault.

OPTIONS:
    -h, --help              Show this help message
    -s, --service NAME      Service name (default: current directory name)
    -a, --alias NAME        SSH host alias (default: service name)
    -v, --vault-path PATH   Vault path for SSH key (default: secret/SERVICE/ssh)
    -f, --key-field FIELD   Vault key field name (default: private_key)
    -k, --key-name NAME     Local SSH key filename (default: SERVICE)
    --vm-ip IP              Override VM IP from vault (default: read from vault)
    --admin-user USER       Override admin user from vault (default: read from vault)

EXAMPLES:
    # Basic usage - reads all details from vault
    ./setup-ssh-from-vault.sh --service fairdom-seek

    # Override specific values
    ./setup-ssh-from-vault.sh --service fairdom-seek --admin-user myuser

    # Custom vault path
    ./setup-ssh-from-vault.sh --service myapp --vault-path secret/prod/myapp/keys

VAULT STORAGE FORMAT:
    The script expects SSH details to be stored in HashiCorp Vault as:
    vault kv put secret/SERVICE/ssh \\
        private_key=@/path/to/private_key \\
        ip_address=1.2.3.4 \\
        admin_user=azureuser \\
        port=22

ENVIRONMENT VARIABLES:
    VAULT_ADDR              HashiCorp Vault server URL
    VAULT_TOKEN             Vault authentication token

EOF
}

# Default configuration
SERVICE_NAME=$(basename "$(pwd)")
SSH_HOST_ALIAS=""
VAULT_PATH=""
PRIVATE_KEY_FIELD="private_key"
SSH_KEY_NAME=""
VM_IP=""
ADMIN_USER=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            usage
            exit 0
            ;;
        -s|--service)
            SERVICE_NAME="$2"
            shift 2
            ;;
        -a|--alias)
            SSH_HOST_ALIAS="$2"
            shift 2
            ;;
        -v|--vault-path)
            VAULT_PATH="$2"
            shift 2
            ;;
        -f|--key-field)
            PRIVATE_KEY_FIELD="$2"
            shift 2
            ;;
        -k|--key-name)
            SSH_KEY_NAME="$2"
            shift 2
            ;;
        --vm-ip)
            VM_IP="$2"
            shift 2
            ;;
        --admin-user)
            ADMIN_USER="$2"
            shift 2
            ;;
        -*)
            echo "ERROR: Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            echo "ERROR: Unexpected positional argument: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set defaults based on service name
SSH_HOST_ALIAS=${SSH_HOST_ALIAS:-$SERVICE_NAME}
SSH_KEY_NAME=${SSH_KEY_NAME:-$SERVICE_NAME}
VAULT_PATH=${VAULT_PATH:-secret/$SERVICE_NAME/ssh}

echo "SSH Configuration Setup with Vault Integration"
echo "============================================="
echo ""
echo "Configuration:"
echo "  Service: $SERVICE_NAME"
echo "  SSH Alias: $SSH_HOST_ALIAS"
echo "  Vault Path: $VAULT_PATH"
echo "  Key Field: $PRIVATE_KEY_FIELD"
echo "  Local Key: ~/.ssh/$SSH_KEY_NAME"
echo ""

# Check required tools
for tool in vault jq; do
    if ! command -v $tool >/dev/null 2>&1; then
        echo "ERROR: $tool is not installed."
        case $tool in
            vault) echo "Download from: https://www.vaultproject.io/downloads" ;;
            jq) echo "Install with: apt-get install jq or brew install jq" ;;
        esac
        exit 1
    fi
done

# Check HashiCorp Vault authentication
echo "Checking HashiCorp Vault authentication..."
if ! vault token lookup >/dev/null 2>&1; then
    echo "ERROR: Not authenticated with HashiCorp Vault."
    echo "  Login with: vault auth -method=<method>"
    echo "  Or set VAULT_TOKEN environment variable"
    exit 1
fi

VAULT_ADDR=${VAULT_ADDR:-"http://127.0.0.1:8200"}
echo "SUCCESS: Authenticated to HashiCorp Vault: $VAULT_ADDR"

# Check if vault path exists
echo "Checking vault path: $VAULT_PATH"
if ! vault kv get "$VAULT_PATH" >/dev/null 2>&1; then
    echo "ERROR: Vault path '$VAULT_PATH' not found or not accessible"
    echo "  Try listing available paths:"
    echo "  vault kv list secret/"
    echo ""
    echo "Expected vault storage format:"
    echo "  vault kv put $VAULT_PATH \\"
    echo "    private_key=@/path/to/private_key \\"
    echo "    ip_address=1.2.3.4 \\"
    echo "    admin_user=azureuser \\"
    echo "    port=22"
    exit 1
fi

# Function to read secret from Vault with error handling
read_vault_secret() {
    local path="$1"
    local key="$2"
    local override_value="$3"

    # Use override if provided
    if [ -n "$override_value" ]; then
        echo "$override_value"
        return 0
    fi

    # Read from vault
    local result=$(vault kv get -format=json "$path" 2>/dev/null | jq -r ".data.data.$key" 2>/dev/null)
    if [ "$result" = "null" ] || [ -z "$result" ]; then
        echo "ERROR: Could not read $key from $path" >&2
        echo "Available fields:" >&2
        vault kv get -format=json "$path" | jq -r '.data.data | keys[]' 2>/dev/null >&2 || echo "Permission denied" >&2
        return 1
    fi
    echo "$result"
}

# Read connection details from Vault (or use overrides)
echo "Reading connection details from Vault..."

VM_IP=$(read_vault_secret "$VAULT_PATH" "ip_address" "$VM_IP")
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to retrieve VM IP address"
    exit 1
fi

ADMIN_USER=$(read_vault_secret "$VAULT_PATH" "admin_user" "$ADMIN_USER")
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to retrieve admin user"
    exit 1
fi

SSH_PORT=$(read_vault_secret "$VAULT_PATH" "port" "")
SSH_PORT=${SSH_PORT:-22}

echo "SUCCESS: Connection details retrieved:"
echo "  Target: $ADMIN_USER@$VM_IP:$SSH_PORT"

# Create SSH directory if it doesn't exist
mkdir -p ~/.ssh

# Backup existing SSH config
echo "Backing up SSH configuration..."
if [ -f ~/.ssh/config ]; then
    cp ~/.ssh/config ~/.ssh/config.backup.$(date +%Y%m%d_%H%M%S)
    echo "SUCCESS: SSH config backed up"
else
    echo "INFO: No existing SSH config found"
fi

# Retrieve private key from HashiCorp Vault
echo "Retrieving SSH private key from HashiCorp Vault..."

if ! vault kv get -field="$PRIVATE_KEY_FIELD" "$VAULT_PATH" > ~/.ssh/$SSH_KEY_NAME 2>/dev/null; then
    echo "ERROR: Could not retrieve private key from vault"
    echo "  Available fields:"
    vault kv get -format=json "$VAULT_PATH" | jq -r '.data.data | keys[]' 2>/dev/null || echo "  Permission denied"
    echo ""
    echo "Expected field name: $PRIVATE_KEY_FIELD"
    exit 1
fi

echo "SUCCESS: Private key retrieved from HashiCorp Vault"

# Set proper permissions on private key
chmod 600 ~/.ssh/$SSH_KEY_NAME
echo "SUCCESS: Private key permissions set (600)"

# Remove or update existing host entry
if [ -f ~/.ssh/config ]; then
    # Remove any existing host entry with the same alias
    sed -i.tmp "/^Host $SSH_HOST_ALIAS$/,/^Host /{ /^Host $SSH_HOST_ALIAS$/d; /^Host /!d; }" ~/.ssh/config
    rm -f ~/.ssh/config.tmp
fi

# Add new SSH config entry
echo "Adding SSH configuration entry..."
cat >> ~/.ssh/config << EOF

Host $SSH_HOST_ALIAS
    HostName $VM_IP
    User $ADMIN_USER
    Port $SSH_PORT
    IdentityFile ~/.ssh/$SSH_KEY_NAME
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
EOF

echo "SUCCESS: SSH config entry added"

# Test SSH connection
echo "Testing SSH connectivity..."
if ssh -o ConnectTimeout=10 $SSH_HOST_ALIAS "echo 'SSH connection successful'" >/dev/null 2>&1; then
    echo "SUCCESS: SSH connection test passed"
else
    echo "WARNING: SSH connection test failed"
    echo "  This may be normal if the VM is still booting"
    echo "  Try manually: ssh $SSH_HOST_ALIAS"
    echo "  Or debug with: ssh -v $SSH_HOST_ALIAS"
fi

echo ""
echo "=============================================="
echo "SSH Configuration Complete!"
echo "=============================================="
echo ""
echo "SSH Access Information:"
echo "  Host Alias: $SSH_HOST_ALIAS"
echo "  Target: $ADMIN_USER@$VM_IP:$SSH_PORT"
echo "  Private Key: ~/.ssh/$SSH_KEY_NAME"
echo ""
echo "Usage:"
echo "  ssh $SSH_HOST_ALIAS"
echo ""
echo "Configuration Details:"
echo "  SSH Config: ~/.ssh/config (backed up)"
echo "  Vault Path: $VAULT_PATH"
echo "  Key Field: $PRIVATE_KEY_FIELD"
echo ""
echo "If connection fails:"
echo "  1. Ensure VM is running and accessible"
echo "  2. Check network security allows SSH from your IP"
echo "  3. Verify the private key matches the public key on the VM"
echo "  4. Debug with: ssh -v $SSH_HOST_ALIAS"
echo ""
