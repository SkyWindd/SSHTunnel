#!/bin/bash
# SSH Tunnel Manager -- Build Script (Linux/Python)
# Neu bi loi "^M bad interpreter": sed -i 's/\r//' build.sh

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo ""
echo -e "${CYAN}=========================================================="
echo "   SSH Tunnel Manager -- Build Script (Linux/Python)"
echo -e "==========================================================${NC}"
echo ""

# ── Kiểm tra Python ───────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}  [LOI] Chua cai Python3!${NC}"
    echo "  Cai: sudo apt install python3 python3-pip"
    exit 1
fi

PYVER=$(python3 --version 2>&1)
echo -e "${GREEN}  [OK] $PYVER${NC}"
echo ""

# ── Tìm đúng lệnh pip ─────────────────────────────────────
# Thử theo thứ tự: pip3, pip, python3 -m pip
PIP_CMD=""
if command -v pip3 &>/dev/null; then
    PIP_CMD="pip3"
elif command -v pip &>/dev/null; then
    PIP_CMD="pip"
elif python3 -m pip --version &>/dev/null 2>&1; then
    PIP_CMD="python3 -m pip"
else
    echo -e "${RED}  [LOI] Khong tim thay pip!${NC}"
    echo "  Cai: sudo apt install python3-pip"
    exit 1
fi
echo -e "${GREEN}  [OK] pip: $PIP_CMD${NC}"

# ── Hàm cài package an toàn ───────────────────────────────
install_package() {
    local pkg=$1
    echo "  Dang cai $pkg..."
    # Thử --break-system-packages trước (Ubuntu 23+)
    $PIP_CMD install "$pkg" -q --break-system-packages 2>/dev/null \
        || $PIP_CMD install "$pkg" -q \
        || python3 -m pip install "$pkg" -q --break-system-packages 2>/dev/null \
        || python3 -m pip install "$pkg" -q
}

# ── Kiểm tra dependencies ─────────────────────────────────
echo "  [1/4] Kiem tra dependencies..."
python3 -c "import cryptography" 2>/dev/null || install_package cryptography
python3 -c "import PyInstaller" 2>/dev/null || install_package pyinstaller
echo -e "${GREEN}  [OK] Dependencies san sang${NC}"
echo ""

# ── Tìm lệnh pyinstaller ──────────────────────────────────
# Thử theo thứ tự: pyinstaller, python3 -m PyInstaller
PYINSTALLER_CMD=""
if command -v pyinstaller &>/dev/null; then
    PYINSTALLER_CMD="pyinstaller"
elif python3 -m PyInstaller --version &>/dev/null 2>&1; then
    PYINSTALLER_CMD="python3 -m PyInstaller"
else
    # Thử tìm trong các đường dẫn phổ biến
    for path in \
        "$HOME/.local/bin/pyinstaller" \
        "/usr/local/bin/pyinstaller" \
        "/usr/bin/pyinstaller" \
        "$(python3 -c 'import site; print(site.getusersitepackages())' 2>/dev/null)/../../../bin/pyinstaller"
    do
        if [ -f "$path" ]; then
            PYINSTALLER_CMD="$path"
            break
        fi
    done
fi

if [ -z "$PYINSTALLER_CMD" ]; then
    echo -e "${RED}  [LOI] Khong tim thay pyinstaller!${NC}"
    echo "  Thu chay thu cong:"
    echo "    python3 -m PyInstaller --version"
    echo "  Neu bao loi 'No module named PyInstaller', cai lai:"
    echo "    pip3 install pyinstaller --break-system-packages"
    exit 1
fi
echo -e "${GREEN}  [OK] PyInstaller: $PYINSTALLER_CMD${NC}"
echo ""

# ── Xóa cache cũ ──────────────────────────────────────────
echo "  [2/4] Xoa cache build cu..."
rm -rf build publish/linux
echo -e "${GREEN}  [OK] Da xoa cache${NC}"
echo ""

# ── Build ─────────────────────────────────────────────────
echo "  [3/4] Dang build SshTunnelManager..."
$PYINSTALLER_CMD SshTunnelManager.spec \
    --distpath publish/linux \
    --workpath build \
    --noconfirm \
    --clean

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}  [LOI] Build that bai!${NC}"
    echo "  Thu chay thu cong de xem loi chi tiet:"
    echo "    python3 -m PyInstaller SshTunnelManager.spec --distpath publish/linux --workpath build --noconfirm --clean"
    exit 1
fi

echo ""
echo "  [4/4] Build hoan tat!"
echo ""

# ── Cấp quyền thực thi ───────────────────────────────────
chmod +x publish/linux/SshTunnelManager
echo -e "${GREEN}  [OK] Da cap quyen thuc thi${NC}"

# ── Xóa file Windows không cần thiết ─────────────────────
rm -f publish/linux/*.exe
rm -f publish/linux/*.pdb
rm -f publish/linux/*.ppk
rm -f publish/linux/*.ppk.enc
echo -e "${GREEN}  [OK] Da xoa cac file Windows khong can thiet${NC}"

# ── Copy run.sh ───────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$SCRIPT_DIR/run.sh" ]; then
    cp "$SCRIPT_DIR/run.sh" publish/linux/
    chmod +x publish/linux/run.sh
    # Fix CRLF nếu bị lỗi line ending
    sed -i 's/\r//' publish/linux/run.sh 2>/dev/null
    echo -e "${GREEN}  [OK] Da copy run.sh${NC}"
fi

# ── Kiểm tra file .pem ───────────────────────────────────
echo ""
echo -e "${CYAN}=========================================================="
echo "                   BUILD THANH CONG"
echo -e "==========================================================${NC}"
echo ""
echo "  Output: publish/linux/SshTunnelManager"
echo ""

if [ -f "publish/linux/default_vps.pem" ]; then
    chmod 600 publish/linux/default_vps.pem
    echo -e "${GREEN}  [OK] default_vps.pem da co san (chmod 600)${NC}"
elif [ -f "publish/linux/default_vps.pem.enc" ]; then
    echo -e "${GREEN}  [OK] default_vps.pem.enc da co san (da ma hoa)${NC}"
else
    echo -e "${YELLOW}  [!] THIEU: file key chua co trong publish/linux/${NC}"
    echo "      Neu co file .pem:"
    echo "        cp /duong/dan/default_vps.pem publish/linux/"
    echo "        chmod 600 publish/linux/default_vps.pem"
    echo "      Neu muon ma hoa key:"
    echo "        cd publish/linux && ./SshTunnelManager --encrypt-key"
fi

echo ""
echo "  Thu muc phan phoi:"
echo "    publish/linux/"
echo "    +-- SshTunnelManager      (binary)"
echo "    +-- default_vps.pem       (file key — hoac .pem.enc neu da ma hoa)"
echo "    +-- run.sh                (launcher)"
echo ""
echo "  Chay app:"
echo "    cd publish/linux && ./run.sh"
echo ""
echo -e "${CYAN}==========================================================${NC}"
echo ""
