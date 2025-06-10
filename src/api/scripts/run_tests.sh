#!/bin/bash

echo "=========================================="
echo "Devengo API Test Runner"
echo "=========================================="

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "OPTIONS:"
    echo "  --all                    Run all tests (default)"
    echo "  --unit                   Run only unit tests"
    echo "  --integration            Run only integration tests" 
    echo "  --coverage               Run tests with coverage report"
    echo "  --file <filename>        Run specific test file"
    echo "  --parallel               Run tests in parallel"
    echo "  --verbose                Run with verbose output"
    echo "  --help                   Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Run all tests"
    echo "  $0 --coverage                        # Run with coverage"
    echo "  $0 --file test_client_service.py     # Run specific file"
    echo "  $0 --unit --parallel                 # Run unit tests in parallel"
}

# Default options
RUN_COVERAGE=false
RUN_PARALLEL=false
VERBOSE=""
TEST_FILE=""
TEST_MARKER=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_usage
            exit 0
            ;;
        --all)
            TEST_MARKER=""
            shift
            ;;
        --unit)
            TEST_MARKER="-m unit"
            shift
            ;;
        --integration)
            TEST_MARKER="-m integration"
            shift
            ;;
        --coverage)
            RUN_COVERAGE=true
            shift
            ;;
        --file)
            TEST_FILE="tests/$2"
            shift 2
            ;;
        --parallel)
            RUN_PARALLEL=true
            shift
            ;;
        --verbose)
            VERBOSE="-vv"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Build the pytest command
PYTEST_CMD="pytest $VERBOSE"

if [ "$RUN_COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=src/api --cov-report=html --cov-report=term"
fi

if [ "$RUN_PARALLEL" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -n auto"
fi

if [ -n "$TEST_MARKER" ]; then
    PYTEST_CMD="$PYTEST_CMD $TEST_MARKER"
fi

if [ -n "$TEST_FILE" ]; then
    PYTEST_CMD="$PYTEST_CMD $TEST_FILE"
fi

# Show what we're about to run
echo "Running command: $PYTEST_CMD"
echo ""

# Run the tests
docker compose -f docker-compose.test.yml run --rm api-test $PYTEST_CMD

# Show results
EXIT_CODE=$?
echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Tests completed successfully!"
else
    echo "❌ Tests failed with exit code: $EXIT_CODE"
fi
echo "=========================================="

exit $EXIT_CODE 