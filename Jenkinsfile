@Library('shared-lib') _
pipeline {
    agent {
        docker {
            image 'sonarsource/sonar-scanner-cli:latest'
            // args '-v -u root:root'  // Ensures access to files if permission issues arise
            userRoot true
        }
    }

    environment {
        SONAR_HOST_URL = 'http://your-sonarqube-host:9000'  // ⚠ Replace with actual accessible URL
        SONAR_LOGIN = credentials('sonarqube')              // ⚠ Ensure this is a "Secret Text" credential
    }

    stages {
        stage('Checkout from GitHub') {
            steps {
                codeClone("master", "https://github.com/vivekdalsaniya12/FaceLog.git")
            }
        }

        stage('Generate Coverage') {
            agent {
                docker {
                    image 'python:3.8-slim'
                }
            }
            steps {
                sh """
                    pip install -r requirements.txt coverage
                    coverage run manage.py test
                    coverage xml
                """
            }
        }

        stage('SonarQube Analysis') {
            steps {
                sh """
                    sonar-scanner \
                        -Dsonar.projectKey=FaceLog \
                        -Dsonar.sources=. \
                        -Dsonar.host.url=${SONAR_HOST_URL} \
                        -Dsonar.login=${SONAR_LOGIN} \
                        -Dsonar.python.coverage.reportPaths=coverage.xml
                """
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
