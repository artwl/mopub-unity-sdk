#!/usr/bin/env groovy
pipeline {
    agent any
    parameters {
        string(name: 'UNITY_ROOT', defaultValue: '/Applications/Unity/Hub/Editor', description: 'Override the root directory of the agent Unity root')
        string(name: 'UNITY_VERSION', defaultValue: '2017.4.32f1', description: 'The version directory name of the Unity install')
    }
    environment {
        UNITY_ROOT = "${params.UNITY_ROOT}"
        UNITY_VERSION = "${params.UNITY_VERSION}"
        UNITY_BIN = "${env.UNITY_ROOT}/${env.UNITY_VERSION}/Unity.app/Contents/MacOS/Unity"
        PARSED_JOB_NAME = URLDecoder.decode(env.JOB_NAME, "UTF-8")
        SLACK_JOB_NAME = "<${env.BUILD_URL}|${PARSED_JOB_NAME} #${env.BUILD_NUMBER}>"
    }

    stages {
        stage('Build SDKs and Unity Package') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'xterm']) {
                    echo "UNITY_ROOT: ${env.UNITY_ROOT}"
                    echo "UNITY_VERSION: ${env.UNITY_VERSION}"
                    echo "UNITY_PATH: ${env.UNITY_BIN}"
                    sh './scripts/build.sh'
                    archiveArtifacts 'mopub-unity-plugin/*.unitypackage'
                }
            }
        }
        stage('Run Unit Tests') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'xterm']) {
                    sh './scripts/run_unit_tests.sh'
                }
            }
        }
        stage('Build Sample Apps') {
            steps {
                wrap([$class: 'AnsiColorBuildWrapper', 'colorMapName': 'xterm']) {
                    sh './scripts/private/build-sample-apps.sh'
                    archiveArtifacts 'unity-sample-app/Build/*.apk'
                    archiveArtifacts 'unity-sample-app/Build/*.ipa.zip'
                    archiveArtifacts 'scripts/*log.txt'
                }
            }
        }
    }
    post {
        success {
            wrap([$class: 'BuildUser']) {
                script {
                    def firstBuild = !currentBuild.previousBuild;
                    def lastBuildResult = !firstBuild && currentBuild.previousBuild.result
                    echo "BUILD SUCCESS!! :aww-yeah:"
                    if (firstBuild || lastBuildResult != currentBuild.result) {
                        slackSend color: 'GREEN', message: "${SLACK_JOB_NAME} has succeeded."
                    }
                    def user = env.BUILD_USER_ID
                    if( user ) {
                        slackSend channel: "@${user}", color: 'GREEN', message: "The build you triggered ${SLACK_JOB_NAME} has succeeded."
                    }
                }
            }
        }
        failure {
            slackSend color: 'RED', message: "Attention @here ${SLACK_JOB_NAME} has failed."
        }
    }
}
