#!/bin/bash

# Start new tmux session if it doesn't exist
tmux new-session -d -s gemini-transcription-beta

# Run the service
tmux send-keys -t gemini-transcription-beta "cd /home/pi/caringmind/services/gemini-transcription/backend" C-m
tmux send-keys -t gemini-transcription-beta "services/gemini-transcription/backend/run_server.sh" C-m
# Attach to the session
tmux attach-session -t gemini-transcription-beta
