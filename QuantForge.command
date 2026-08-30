#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
"$DIR/scripts/start_quantforge.sh"
open "http://127.0.0.1:8080"
