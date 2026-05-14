#!/bin/bash
# disk-usage skill: 查看磁盘使用情况
# 参数通过 stdin 以 JSON 格式传入

INPUT=$(cat)

PATH_TO_CHECK="/"
if command -v python3 &> /dev/null; then
    PATH_TO_CHECK=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('path','/'))" 2>/dev/null || echo "/")
elif command -v python &> /dev/null; then
    PATH_TO_CHECK=$(echo "$INPUT" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('path','/'))" 2>/dev/null || echo "/")
fi

echo "Disk Usage:"
echo ""

if command -v powershell.exe &> /dev/null; then
    DRIVE=$(echo "${PATH_TO_CHECK:0:1}" | tr '[:upper:]' '[:lower:]')
    if [[ -z "$DRIVE" || "$DRIVE" == "/" ]]; then
        DRIVE="c"
    fi
    df -h "/mnt/${DRIVE}" --output=source,size,used,avail,pcent 2>/dev/null || \
    df -h "/mnt/${DRIVE}" 2>/dev/null || \
    echo "(Cannot get disk info for ${DRIVE}:)"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    DRIVE="${PATH_TO_CHECK:0:1}"
    if [[ -z "$DRIVE" || "$DRIVE" == "/" ]]; then
        DRIVE="C"
    fi
    wmic logicaldisk where "DeviceID='${DRIVE}:'" get Size,FreeSpace /format:list 2>/dev/null || \
    echo "(Cannot get disk info)"
else
    df -h "$PATH_TO_CHECK" 2>/dev/null || echo "(Cannot get disk info)"
fi