#!/bin/bash

# Enhanced deployment script with better debugging
# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Try to find SSH key in multiple locations
if [ -f "$PROJECT_ROOT/oneacre-prod.pem" ]; then
    SSH_KEY="$PROJECT_ROOT/oneacre-prod.pem"
elif [ -f "$SCRIPT_DIR/oneacre-prod.pem" ]; then
    SSH_KEY="$SCRIPT_DIR/oneacre-prod.pem"
elif [ -f "./oneacre-prod.pem" ]; then
    SSH_KEY="./oneacre-prod.pem"
else
    SSH_KEY="oneacre-prod.pem"  # Fallback, will check later
fi

SERVER_HOST="43.204.148.243"
DOMAIN="gis-portal.1acre.in"  # Domain for deployment
ANSIBLE_USER="ubuntu"

echo "🚀 Enhanced GIS DB API deployment to AWS EC2..."
echo "📁 Script directory: $SCRIPT_DIR"
echo "📁 Project root: $PROJECT_ROOT"
echo "🔑 SSH key: $SSH_KEY"

# Function to test SSH connection with better diagnostics
test_ssh_connection() {
    echo "🔐 Testing SSH connection with diagnostics..."
    
    # Test 1: Basic ping
    echo "📡 Testing basic connectivity (ping)..."
    if ping -c 3 $SERVER_HOST > /dev/null 2>&1; then
        echo "✅ Server is reachable via ping"
    else
        echo "❌ Server is NOT reachable via ping"
        echo "   This could indicate network issues or server is down"
    fi
    
    # Test 2: Check if port 22 is open
    echo "🔍 Testing SSH port 22..."
    if timeout 10 bash -c "</dev/tcp/$SERVER_HOST/22" 2>/dev/null; then
        echo "✅ Port 22 is open and accessible"
    else
        echo "❌ Port 22 is NOT accessible"
        echo "   This is likely a Security Group issue"
        echo "   📋 Fix: Add inbound rule for SSH (port 22) in AWS Security Group"
        return 1
    fi
    
    # Test 3: SSH key permissions
    echo "🔑 Checking SSH key permissions..."
    if [ -f "$SSH_KEY" ]; then
        KEY_PERMS=$(stat -c "%a" "$SSH_KEY" 2>/dev/null || stat -f "%A" "$SSH_KEY" 2>/dev/null)
        if [ "$KEY_PERMS" = "400" ]; then
            echo "✅ SSH key permissions are correct (400)"
        else
            echo "⚠️  SSH key permissions are $KEY_PERMS, should be 400"
            chmod 400 "$SSH_KEY"
            echo "✅ Fixed SSH key permissions"
        fi
    else
        echo "❌ SSH key file not found: $SSH_KEY"
        return 1
    fi
    
    # Test 4: Actual SSH connection
    echo "🔗 Testing SSH authentication..."
    if timeout 15 ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes "$ANSIBLE_USER@$SERVER_HOST" "echo 'SSH connection successful'" 2>/dev/null; then
        echo "✅ SSH connection successful!"
        return 0
    else
        echo "❌ SSH connection failed"
        echo "📋 Try manual SSH for more details:"
        echo "   ssh -v -i \"$SSH_KEY\" $ANSIBLE_USER@$SERVER_HOST"
        return 1
    fi
}

# Function to check AWS Security Group recommendations
check_security_recommendations() {
    echo ""
    echo "🛡️  AWS Security Group Requirements:"
    echo "   Please ensure your EC2 Security Group has these inbound rules:"
    echo ""
    echo "   📡 SSH Access (Required for deployment):"
    echo "      Type: SSH, Protocol: TCP, Port: 22, Source: 0.0.0.0/0"
    echo ""
    echo "   🌐 Web Access (Required for application):"
    echo "      Type: HTTP, Protocol: TCP, Port: 80, Source: 0.0.0.0/0"
    echo "      Type: HTTPS, Protocol: TCP, Port: 443, Source: 0.0.0.0/0"
    echo ""
    echo "   💡 To fix this:"
    echo "      1. Go to AWS Console → EC2 → Security Groups"
    echo "      2. Find security group for instance $SERVER_HOST"
    echo "      3. Add the above inbound rules"
    echo "      4. Wait 1-2 minutes for changes to take effect"
    echo ""
}

# Run SSH diagnostics
# NOTE: Connectivity tests are skipped since manual SSH works
# If you need to re-enable these tests, uncomment the lines below
# if ! test_ssh_connection; then
#     echo ""
#     echo "❌ Cannot connect to server via SSH"
#     check_security_recommendations
#     echo "🔄 Please fix the connection issue and try again"
#     exit 1
# fi

echo "⏭️  Skipping connectivity tests (manual SSH confirmed working)..."

# Check if Ansible is installed
if ! command -v ansible-playbook &> /dev/null; then
    echo "📦 Installing Ansible..."
    pip3 install ansible
    if [ $? -ne 0 ]; then
        echo "❌ Failed to install Ansible. Please install manually:"
        echo "   pip3 install ansible"
        exit 1
    fi
fi

echo "✅ Ansible is available"

# Validate SSH key exists and has correct permissions
if [ ! -f "$SSH_KEY" ]; then
    echo "❌ SSH key not found: $SSH_KEY"
    echo "   Please ensure oneacre-prod.pem exists in:"
    echo "   - $PROJECT_ROOT/"
    echo "   - $SCRIPT_DIR/"
    echo "   - Current directory"
    exit 1
fi

# Fix SSH key permissions if needed
KEY_PERMS=$(stat -c "%a" "$SSH_KEY" 2>/dev/null || stat -f "%A" "$SSH_KEY" 2>/dev/null)
if [ "$KEY_PERMS" != "400" ]; then
    echo "🔧 Fixing SSH key permissions..."
    chmod 400 "$SSH_KEY"
    echo "✅ SSH key permissions set to 400"
fi

# Get absolute path to SSH key
SSH_KEY_ABS=$(cd "$(dirname "$SSH_KEY")" && pwd)/$(basename "$SSH_KEY")

# Create temporary inventory file with better timeout settings
INVENTORY_FILE="/tmp/inventory_aws_gis_db.ini"
cat > "$INVENTORY_FILE" << EOF
[aws_servers]
gis-db-server ansible_host=$SERVER_HOST

[aws_servers:vars]
ansible_user=$ANSIBLE_USER
ansible_ssh_private_key_file=$SSH_KEY_ABS
ansible_ssh_common_args='-o StrictHostKeyChecking=no -o ConnectTimeout=30 -o ServerAliveInterval=30 -o ServerAliveCountMax=10 -o ControlMaster=auto -o ControlPersist=30m -o ControlPath=/tmp/ansible-ssh-%%h-%%p-%%r'
ansible_python_interpreter=/usr/bin/python3
ansible_timeout=3600
timeout=3600
EOF

echo "✅ Inventory file created with enhanced timeouts"

# Change to deployment directory
cd "$SCRIPT_DIR" || {
    echo "❌ Cannot change to deployment directory: $SCRIPT_DIR"
    exit 1
}

# Check if deploy.yml exists
if [ ! -f "deploy.yml" ]; then
    echo "❌ deploy.yml not found in $SCRIPT_DIR"
    echo "Please ensure deploy.yml is in the deployment directory"
    exit 1
fi

echo "✅ deploy.yml found in $SCRIPT_DIR"

# Run the Ansible playbook with enhanced verbosity
echo "🚀 Running Ansible playbook..."
echo "================================================"
echo "📋 Configuration:"
echo "   Server: $SERVER_HOST"
echo "   Domain: $DOMAIN"
echo "   User: $ANSIBLE_USER"
echo "   SSH Key: $SSH_KEY_ABS"
echo "   Playbook: $SCRIPT_DIR/deploy.yml"
echo "================================================"
echo ""

# Run with more verbose output and better error handling
# Use -v for normal verbosity (change to -vv or -vvv for more debugging)
# Increased timeout for long operations like Docker builds
ansible-playbook -i "$INVENTORY_FILE" deploy.yml -v --timeout=3600 --ssh-common-args='-o ServerAliveInterval=30 -o ServerAliveCountMax=10'

# Check deployment result
ANSIBLE_EXIT_CODE=$?

if [ $ANSIBLE_EXIT_CODE -eq 0 ]; then
    echo "================================================"
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "🌐 Your application should be available at:"
    echo "   🔒 HTTPS: https://$DOMAIN"
    echo "   📱 HTTP:  http://$DOMAIN (redirects to HTTPS)"
    echo "   🔗 API Docs: https://$DOMAIN/docs"
    echo "   📖 ReDoc: https://$DOMAIN/redoc"
    echo "   ❤️  Health: https://$DOMAIN/health"
    echo ""
    echo "🔍 Quick health checks:"
    echo "   curl -I https://$DOMAIN/health"
    echo "   curl -I http://$DOMAIN"
    echo ""
    echo "📊 Post-deployment commands:"
    echo "   ssh -i \"$SSH_KEY\" $ANSIBLE_USER@$SERVER_HOST"
    echo "   cd /opt/gis_db/deployment"
    echo "   docker-compose ps"
    echo "   docker-compose logs -f web"
    echo ""
    echo "🗂️ Next steps:"
    echo "   1. Test the application at https://$DOMAIN"
    echo "   2. Check API documentation at https://$DOMAIN/docs"
    echo "   3. Upload sample GIS data files"
else
    echo "================================================"
    echo "❌ Deployment failed with exit code $ANSIBLE_EXIT_CODE"
    echo ""
    echo "🔍 Debug steps:"
    echo "   1. Check the Ansible output above for specific errors"
    echo "   2. SSH manually to debug: ssh -i \"$SSH_KEY\" $ANSIBLE_USER@$SERVER_HOST"
    echo "   3. Check AWS Security Groups again"
    echo "   4. Verify server is running and healthy"
    echo ""
    echo "📞 Common solutions:"
    echo "   - Add SSH (port 22) to Security Group"
    echo "   - Add HTTP (port 80) and HTTPS (port 443) to Security Group"
    echo "   - Restart the EC2 instance if needed"
    echo "   - Check disk space on server"
fi

# Clean up temporary inventory file
rm -f "$INVENTORY_FILE"
echo "🧹 Cleaned up temporary files"
echo ""

if [ $ANSIBLE_EXIT_CODE -eq 0 ]; then
    echo "🌟 Your GIS DB API application is now deployed and ready!"
    echo "   Domain: https://$DOMAIN"
    echo "   Server: $SERVER_HOST"
else
    echo "💡 Need help? The most common issue is AWS Security Group configuration"
    check_security_recommendations
fi
