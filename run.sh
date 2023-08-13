#!/usr/bin/env bash

function show_usage {
    echo "Usage: $0 [OPTIONS] parameter1 parameter2 ..."
    echo "Options:"
    echo "  -e, --env        Environment"
    echo "  -p, --project    Project directoru"
    echo "  -h, --help       Show this help message and exit"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--env)
            environment="$2"
            shift 2
            ;;
        -p|--project)
            project="$2"
            shift 2
            ;;
        -a|--action)
            action="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        -*)
            echo "Error: Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

environment="${environment:-dev}"
project="${project:-$project}"

full_env="${project}/${environment}"
full_env=${full_env//\//.}
root_dir=$(realpath .)

PYTHONPATH=$root_dir exec pulumi $action -s $environment -C $project
