#!/bin/bash

CONTAINER_NAME="tilemaps-app"
IMAGE_NAME="tilemaps-generator"

function show_help {
    echo "Tilemaps Generator CLI Wrapper"
    echo "Usage: $0 [COMMAND] [ARGS]"
    echo ""
    echo "Commands:"
    echo "  build           Build the Docker image ($IMAGE_NAME)"
    echo "  run [args]      Run the application (foreground)"
    echo "  start [args]    Run the application in the background (detached)"
    echo "  logs            Follow the logs of the running container"
    echo "  kill            Stop and remove the running container"
    echo "  help            Show this help message"
    echo ""
    echo "Application Arguments (passed to 'run' or 'start'):"
    echo "  --asset {all,img,mesh}"
    echo "  --process-all-nodes"
    echo "  --disable-lod"
    echo "  --output-json PATH"
    echo "  --existing-db PATH"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 run --asset img"
    echo "  $0 start --asset all (Runs in background)"
    echo "  $0 logs"
}

if [ $# -eq 0 ]; then
    show_help
    exit 1
fi

COMMAND="$1"
shift

case "$COMMAND" in
    build)
        echo "Building Docker image..."
        docker build -t $IMAGE_NAME .
        ;;
    run)
        # Check if container exists
        if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
             echo "Cleaning up previous container..."
             docker rm -f $CONTAINER_NAME > /dev/null
        fi

        echo "Starting container (foreground)..."
        docker run --rm \
          --name $CONTAINER_NAME \
          --env-file ./.env \
          -v "$(pwd):/app" \
          $IMAGE_NAME \
          "$@"
        ;;
    start)
        # Check if container exists
        if [ "$(docker ps -aq -f name=$CONTAINER_NAME)" ]; then
             echo "Cleaning up previous container..."
             docker rm -f $CONTAINER_NAME > /dev/null
        fi

        echo "Starting container (detached)..."
        docker run --rm -d \
          --name $CONTAINER_NAME \
          --env-file ./.env \
          -v "$(pwd):/app" \
          $IMAGE_NAME \
          "$@"
        echo "Container started in background. Use '$0 logs' to view output."
        ;;
    logs)
        docker logs -f $CONTAINER_NAME
        ;;
    kill|stop)
        echo "Stopping container..."
        docker rm -f $CONTAINER_NAME
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'"
        show_help
        exit 1
        ;;
esac