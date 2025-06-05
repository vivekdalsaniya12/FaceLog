@Library('shared-lib') _
pipeline {

    agent any

    // environment {
    //     // place here any environment variables you need
    // }

    stages {
        stage('Checkout from GitHub') {
            steps {
                codeClone("master", "https://github.com/vivekdalsaniya12/FaceLog.git")
            }
        }

        stage('Docker Build') {
            steps {
                dockerBuild("vivekdalsaniya/facelog", "latest", ".")
            }
        }

        stage('Docker Push') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockercreds', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
                    dockerPush("${USERNAME}", "${PASSWORD}", "vivekdalsaniya/facelog", "latest")
                }
            }
        }
    }
}
