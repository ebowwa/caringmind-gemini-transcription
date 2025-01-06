#!/bin/bash

# Annotations and description
# This script generates a project.yml file for XcodeGen based on environment variables
# It handles error checking and provides clear feedback
# Requirements: 
# - .env file with required variables
# - XcodeGen installed (brew install xcodegen)

set -e  # Exit on any error

# Load environment variables
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please copy .env.example to .env and fill in your values."
    exit 1
fi

source .env

# Validate required environment variables
required_vars=(
    "APP_NAME"
    "BUNDLE_ID"
    "DEPLOYMENT_TARGET"
    "SWIFT_VERSION"
    "GOOGLE_API_KEY"
    "DEVELOPMENT_TEAM"
)

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "Error: $var is not set in .env file"
        exit 1
    fi
done

# Generate project.yml
cat > project.yml << EOL
name: ${APP_NAME}
options:
  bundleIdPrefix: ${BUNDLE_ID}
  deploymentTarget:
    iOS: ${DEPLOYMENT_TARGET}
  xcodeVersion: "15.0"
settings:
  base:
    SWIFT_VERSION: ${SWIFT_VERSION}
    DEVELOPMENT_TEAM: \${DEVELOPMENT_TEAM}
targets:
  ${APP_NAME}:
    type: application
    platform: iOS
    sources:
      - path: Sources
    settings:
      base:
        PRODUCT_BUNDLE_IDENTIFIER: ${BUNDLE_ID}
        INFOPLIST_FILE: Sources/Info.plist
        MARKETING_VERSION: "1.0.0"
        CURRENT_PROJECT_VERSION: "1"
    info:
      path: Sources/Info.plist
      properties:
        CFBundleName: ${APP_NAME}
        CFBundleDisplayName: ${APP_NAME}
        CFBundleIdentifier: ${BUNDLE_ID}
        CFBundleVersion: "1"
        CFBundleShortVersionString: "1.0.0"
        UILaunchStoryboardName: LaunchScreen
        UIApplicationSceneManifest:
          UIApplicationSupportsMultipleScenes: false
          UISceneConfigurations:
            UIWindowSceneSessionRoleApplication:
              - UISceneConfigurationName: Default Configuration
                UISceneDelegateClassName: \$(PRODUCT_MODULE_NAME).SceneDelegate
        NSMicrophoneUsageDescription: "We need access to your microphone for audio transcription"
        UIBackgroundModes:
          - audio
EOL

# Create basic project structure
mkdir -p Sources

# Generate Info.plist template if it doesn't exist
if [ ! -f Sources/Info.plist ]; then
    echo "Creating Info.plist from project.yml configuration..."
    xcodegen generate
fi

# Generate Xcode project and open it
xcodegen generate
open "${APP_NAME}.xcodeproj"

echo "Project configuration generated and opened in Xcode successfully!"
