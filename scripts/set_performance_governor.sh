#!/bin/bash
# Set CPU governor to performance mode
# Run with sudo for best results

echo "Setting CPU governor to performance mode..."

# Check current governor
CURRENT=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "unknown")
echo "Current governor: $CURRENT"

# Try cpufreq-set first
if command -v cpufreq-set &> /dev/null; then
    for cpu in /sys/devices/system/cpu/cpu[0-9]*; do
        cpu_num=$(basename $cpu | sed 's/cpu//')
        sudo cpufreq-set -c $cpu_num -g performance 2>/dev/null
    done
    echo "Set governor using cpufreq-set"
else
    # Direct sysfs write
    for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo "performance" | sudo tee $gov > /dev/null 2>&1
    done
    echo "Set governor via sysfs"
fi

# Verify
NEW=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "unknown")
echo "New governor: $NEW"

if [ "$NEW" = "performance" ]; then
    echo "Success: CPU governor set to performance"
    exit 0
else
    echo "Warning: Could not verify governor change"
    exit 1
fi
