#!/usr/bin/env bash
my_dir="$(dirname $0)"
source "$my_dir/../validate.sh"
source "$my_dir/../print_helpers.sh"

ensure_unity_bin

PROJECT_PATH="$PWD/unity-sample-app"
OUT_DIR="$PROJECT_PATH/Build"
BUILD_LOG_NAME="buildlog.txt"
IOS_BUILD_AIDS_DIR="$PROJECT_PATH/iOSBuildAids"
IOS_EXPORT_PLIST="$IOS_BUILD_AIDS_DIR/ExportOptions.plist"
XCODE_TEAM_ID="4S7XS533V3"

function build_sample_app
{
  platform=$1
  last_commit=`git rev-parse --short HEAD`
  build_log=$my_dir/../$platform$BUILD_LOG_NAME
  
  echo -e "Current Directory: $PWD\n"

  echo -e "Running Unity build for $platform...\n"
  $UNITY_BIN -buildTarget $platform -executeMethod MoPubSampleBuild.PerformBuild lastCommit=$last_commit -projectPath $PROJECT_PATH -force-free -quit -batchmode -logFile $build_log >& /dev/null
  ls $OUT_DIR/*$platform*$last_commit* >& /dev/null
  validate "Building the $platform sample app has failed, please check $build_log\nMake sure Unity isn't running when invoking this script!"
  
  if [ $platform = iOS ]; then
    cd $OUT_DIR/*$platform*$last_commit*
    echo -e "Current Directory: $PWD\n"
    ls -lt

    echo -e "Setting XCode development team...\n"
    sed -i "" -e "/ *DEVELOPMENT_TEAM = .*/s/= \"\"/= $XCODE_TEAM_ID/" Unity-iPhone.xcodeproj/project.pbxproj
    validate

    echo -e "Running XCode archive...\n"
    xcodebuild -workspace Unity-iPhone.xcworkspace -scheme Unity-iPhone clean archive -configuration release -sdk iphoneos -archivePath Unity-iPhone.xcarchive -verbose
    validate

    echo -e "Running XCode export...\n"
    xcodebuild -exportArchive -archivePath  Unity-iPhone.xcarchive -exportOptionsPlist  $IOS_EXPORT_PLIST -exportPath  Unity-iPhone.ipa
    validate

    echo -e "Zipping .ipa..."
    filename=`ls $OUT_DIR | grep iOS | grep $last_commit`
    zip -jr $OUT_DIR/$filename.ipa.zip $OUT_DIR/$filename/Unity-iPhone.ipa/
    validate
  fi
}

print_blue_line "Building sample apps..."

build_sample_app Android
build_sample_app iOS

print_green_line "Done building sample apps!"
