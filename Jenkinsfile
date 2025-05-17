@Library('shared-lib') _
pipeline {
    agent { 
        label 'home' ,
        docker {
            image 'sonarsource/sonar-scanner-cli'
            args '-v'
        } 
    }
    environment {
        SONAR_HOST_URL = 'http://localhost:9000'
        SONAR_LOGIN = credentials('sonarqube')
    }

    stages {
        stage('checkout from Github') {
            steps {
                codeClone("master","https://github.com/vivekdalsaniya12/FaceLog.git")
            }
        }
        
        stage('Generate coverage') {
            steps {
                sh """
                    pip install coverage
                    coverage run manage.py test
                    coverage xml
                    """
            }
        }
        
        stage('SonarQube Analysis') {
            steps {
                sh '''
                    sonar-scanner \
                        -Dsonar.projectKey=FaceLog \
                        -Dsonar.sources=. \
                        -Dsonar.host.url=$SONAR_HOST_URL \
                        -Dsonar.login=$SONAR_LOGIN \
                        -Dsonar.python.coverage.reportPaths=coverage.xml
                '''
            }
        }
        
        stage('Docker build') {
            steps {
                dockerBuild("vivekdalsaniya/facelog","latest",".")
            }
        }
        
        stage('Docker Push') {
            steps {
                withCredentials ([usernamePassword(credentialsId:'dockercreds',usernameVariable:'USERNAME',passwordVariable:'PASSWORD')]) 
                {
                    dockerPush("${USERNAME}","${PASSWORD}","vivekdalsaniya/facelog","latest")
                }
            }
        }
        
    }
}
