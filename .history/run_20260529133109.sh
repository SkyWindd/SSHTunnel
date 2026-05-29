#!/bin/bash
# SSH Tunnel Manager -- Launcher (Linux)
# User chi can: chmod +x run.sh && ./run.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SCRIPT_DIR/SshTunnelManager"
PEM="$SCRIPT_DIR/default_vps.pem"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fix CRLF neu file duoc tao tren Windows
if file "$0" 2>/dev/null | grep -q CRLF; then
    sed -i 's/\r//' "$0"
    exec bash "$0" "$@"
fi

# Tu dong cai SSH Server neu chua co
if ! command -v sshd &>/dev/null; then
    echo -e "${YELLOW}  [SSH] Chua co SSH server, dang cai dat...${NC}"
    sudo apt update -qq && sudo apt install openssh-server -y -qq
    echo -e "${GREEN}  [SSH] Cai dat hoan tat!${NC}"
fi

# Bat PasswordAuthentication
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication yes/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config

# Tu dong bat SSH Server neu chua chay
if ! sudo service ssh status 2>/dev/null | grep -qE "running|active"; then
    echo -e "${YELLOW}  [SSH] Dang bat SSH server...${NC}"
    sudo service ssh start 2>/dev/null
    echo -e "${GREEN}  [SSH] SSH server da chay!${NC}"
fi

# Kiem tra binary
if [ ! -f "$APP" ]; then
    echo -e "${RED}  [LOI] Khong tim thay SshTunnelManager!${NC}"
    echo "  Dam bao thu muc co: SshTunnelManager, default_vps.pem, run.sh"
    exit 1
fi

# Fix permission file .pem
if [ -f "$PEM" ]; then
    PERM=$(stat -c "%a" "$PEM" 2>/dev/null)
    if [ "$PERM" != "600" ]; then
        chmod 600 "$PEM"
        echo -e "${YELLOW}  [FIX] chmod 600 default_vps.pem${NC}"
    fi
else
    echo -e "${YELLOW}  [CANH BAO] Khong tim thay default_vps.pem${NC}"
fi

# Cap quyen thuc thi neu thieu
[ ! -x "$APP" ] && chmod +x "$APP"

# Chay app
exec "$APP" "$@"
