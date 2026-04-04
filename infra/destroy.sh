#!/bin/bash
# Destroy all AWS resources (stop paying if free tier expires)
set -euo pipefail

cd "$(dirname "$0")"

echo "This will DESTROY all AWS resources for quantum-circuit-sim."
echo "Press Ctrl+C to cancel, or Enter to continue."
read -r

terraform destroy -auto-approve

echo "All resources destroyed."
