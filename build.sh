#!/bin/bash

# Docker image build script with multi-platform support
# Usage: ./build.sh [options]
# Options:
#   -p, --platform PLATFORM    Target platform (default: linux/amd64)
#                               Examples: linux/amd64, linux/arm64, linux/arm/v7
#                               Use comma for multiple platforms: linux/amd64,linux/arm64
#   -t, --tag TAG              Image tag (default: weread-playwright:latest)
#   -n, --name NAME            Image name (default: weread-playwright)
#   --push                     Push image to registry after build (required for multi-platform)
#   -h, --help                 Show this help message

set -e

# Default values
DEFAULT_PLATFORM="linux/amd64"
DEFAULT_NAME="weread-playwright"
DEFAULT_TAG="latest"

# Parse arguments
PLATFORM="$DEFAULT_PLATFORM"
IMAGE_NAME="$DEFAULT_NAME"
IMAGE_TAG="$DEFAULT_TAG"
PUSH_IMAGE=false

show_help() {
    grep '^#' "$0" | sed 's/^# //g' | sed 's/^#//g' | head -n 15
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        --push)
            PUSH_IMAGE=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            ;;
    esac
done

FULL_IMAGE_NAME="${IMAGE_NAME}:${IMAGE_TAG}"

# Check if docker buildx is available
if ! docker buildx version &> /dev/null; then
    echo "Error: docker buildx is not available. Please install Docker Buildx."
    exit 1
fi

# Create/use buildx builder
BUILDER_NAME="weread-builder"
if ! docker buildx inspect "$BUILDER_NAME" &> /dev/null; then
    echo "Creating buildx builder: $BUILDER_NAME"
    docker buildx create --name "$BUILDER_NAME" --driver docker-container --use
else
    echo "Using existing buildx builder: $BUILDER_NAME"
    docker buildx use "$BUILDER_NAME"
fi

echo "=========================================="
echo "Docker Image Build Configuration"
echo "=========================================="
echo "Platform(s): $PLATFORM"
echo "Image: $FULL_IMAGE_NAME"
echo "Push: $PUSH_IMAGE"
echo "=========================================="

# Build arguments
BUILD_ARGS=(
    --platform "$PLATFORM"
    -t "$FULL_IMAGE_NAME"
)

# Add --push flag if pushing to registry
if [ "$PUSH_IMAGE" = true ]; then
    BUILD_ARGS+=(--push)
    echo "Note: Image will be pushed to registry after build"
else
    BUILD_ARGS+=(--load)
    # Warn if building for multiple platforms without push
    if [[ "$PLATFORM" == *","* ]]; then
        echo "Warning: Building for multiple platforms without --push."
        echo "         Only the current platform will be loaded locally."
        echo "         Use --push to build and push all platforms."
    fi
fi

echo ""
echo "Building image..."
echo "Command: docker buildx build ${BUILD_ARGS[@]} ."
echo ""

# Build the image
docker buildx build "${BUILD_ARGS[@]}" .

echo ""
echo "=========================================="
echo "Build completed successfully!"
echo "=========================================="

if [ "$PUSH_IMAGE" = false ]; then
    echo "Image available locally: $FULL_IMAGE_NAME"
    echo ""
    echo "Run container:"
    echo "  docker run -d -v \$(pwd)/data:/app/data --env-file .env $FULL_IMAGE_NAME"
else
    echo "Image pushed to registry: $FULL_IMAGE_NAME"
fi
echo "=========================================="
