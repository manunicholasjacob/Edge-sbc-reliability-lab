#!/bin/bash
# Run all benchmarks script
# Edge SBC Reliability Lab - Full benchmark suite execution

set -e

# Configuration
CONFIG_DIR="${CONFIG_DIR:-configs}"
OUTPUT_DIR="${OUTPUT_DIR:-results}"
COOLDOWN_TEMP="${COOLDOWN_TEMP:-50}"
COOLDOWN_TIMEOUT="${COOLDOWN_TIMEOUT:-300}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=============================================="
echo "Edge SBC Reliability Lab - Full Benchmark Suite"
echo "=============================================="
echo ""

# Check if running on Raspberry Pi
if [ -f /proc/device-tree/model ]; then
    MODEL=$(cat /proc/device-tree/model)
    echo "Device: $MODEL"
else
    echo -e "${YELLOW}Warning: Not running on Raspberry Pi${NC}"
fi

# Check Python environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Not in a virtual environment${NC}"
    echo "Consider activating venv: source venv/bin/activate"
fi

# Pre-run health check
echo ""
echo "Running pre-benchmark health check..."
python -m edge_sbc_reliability_lab.scripts.pre_run_health_check

if [ $? -ne 0 ]; then
    echo -e "${RED}Health check failed. Aborting.${NC}"
    exit 1
fi

# Set CPU governor to performance (requires sudo)
echo ""
echo "Setting CPU governor to performance..."
if command -v cpufreq-set &> /dev/null; then
    sudo cpufreq-set -g performance 2>/dev/null || echo "Could not set governor (may require sudo)"
else
    echo "cpufreq-set not available"
fi

# Run the benchmark suite
echo ""
echo "Starting benchmark suite..."
echo "Config directory: $CONFIG_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

python -m edge_sbc_reliability_lab.reproducibility.run_all \
    --config-dir "$CONFIG_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --cooldown-temp "$COOLDOWN_TEMP" \
    --cooldown-timeout "$COOLDOWN_TIMEOUT"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=============================================="
    echo "Benchmark suite completed successfully!"
    echo "=============================================="
    echo -e "${NC}"
else
    echo ""
    echo -e "${RED}=============================================="
    echo "Benchmark suite completed with errors"
    echo "=============================================="
    echo -e "${NC}"
fi

exit $EXIT_CODE
