#!/bin/bash
# Generate self-signed TLS certificates for local development
# Usage: ./nginx/generate-certs.sh

set -e

CERT_DIR="$(dirname "$0")/certs"
mkdir -p "$CERT_DIR"

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout "$CERT_DIR/key.pem" \
  -out "$CERT_DIR/cert.pem" \
  -subj "/C=US/ST=Local/L=Local/O=AI Nurse/CN=localhost"

echo "Certificates generated in $CERT_DIR"
echo "  cert.pem (public certificate)"
echo "  key.pem  (private key)"
