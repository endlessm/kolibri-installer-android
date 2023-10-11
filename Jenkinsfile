// Jenkins pipeline
// https://www.jenkins.io/doc/book/pipeline/
//
// Required parameters: UPLOAD

pipeline {
    agent {
        dockerfile {
            // Try to use the same node to make use of caching.
            reuseNode true
        }
    }

    environment {
        // pre-commit, Gradle and the Android Gradle Plugin cache outputs in
        // the home directory. Point them inside the workspace.
        XDG_CACHE_HOME = "$WORKSPACE/_cache"
        GRADLE_USER_HOME = "$WORKSPACE/_cache/.gradle"
        ANDROID_USER_HOME = "$WORKSPACE/_cache/.android"

        // Set the versionCode property based on the build number. At one point
        // a release was made from the PR job, which had a build number far
        // ahead of the standard job.
        ORG_GRADLE_PROJECT_versionCode = "${currentBuild.number + 169}"
    }


    options {
        ansiColor('xterm')

        // This is needed to allow the upload job to copy the built
        // artifacts.
        copyArtifactPermission('kolibri-installer-android-upload')
    }

    stages {
        stage('Lint') {
            steps {
                sh 'pre-commit run --all-files --show-diff-on-failure'
            }
        }

        stage('Test') {
            steps {
                sh './gradlew check'
            }
        }

        stage('APK') {
            steps {
                sh './gradlew build'
                archiveArtifacts artifacts: 'app/build/outputs/apk/*/*.apk, app/build/outputs/version-*.json'
            }
        }

        stage('AAB') {
            // Don't create signed bundles for PRs.
            when {
                expression { !params.ghprbPullId }
            }

            steps {
                withCredentials(
                    [[$class: 'VaultCertificateCredentialsBinding',
                      credentialsId: 'google-play-upload-key',
                      keyStoreVariable: 'UPLOAD_KEYSTORE',
                      passwordVariable: 'UPLOAD_PASSWORD']]
                ) {
                    writeFile(
                        file: 'upload.properties',
                        text: """\
                              storeFile=${env.UPLOAD_KEYSTORE}
                              storePassword=${env.UPLOAD_PASSWORD}
                              keyAlias=upload
                              """.stripIndent(),
                    )
                    sh './gradlew bundle'
                    archiveArtifacts artifacts: 'app/build/outputs/bundle/*/*.aab'
                }
            }
        }
    }

    post {
        always {
            buildDescription("UPLOAD=${params.UPLOAD}")
        }

        cleanup {
            sh 'rm -f upload.properties'
        }

        success {
            script {
                if (!params.ghprbPullId && params.UPLOAD) {
                    echo "Upload the built Kolibri Android packages for internal testers"
                    build(
                        job: 'kolibri-installer-android-upload',
                        parameters: [
                            string(name: 'RELEASE_NOTES', value: '[]'),
                        ]
                    )
                }
            }
        }

        failure {
            // Send email on failures when this not a PR. Unfortunately,
            // there's no declarative pipeline step to test for this
            // besides wrapping in a script block and checking for one
            // of the ghprb environment variables.
            script {
                if (!env.ghprbPullId) {
                    emailext (
                        to: 'apps@endlessos.org,$DEFAULT_RECIPIENTS',
                        replyTo: 'apps@endlessos.org',
                        subject: '$DEFAULT_SUBJECT',
                        body: '$DEFAULT_CONTENT',
                    )
                }
            }
        }
    }
}
