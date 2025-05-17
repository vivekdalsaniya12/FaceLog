@Library('shared-lib') _
pipeline {
    agent { label 'home' }

    stages {
        stage('checkout from Github') {
            steps {
                codeClone("master","https://github.com/vivekdalsaniya12/FaceLog.git")
            }
        }
        
        stage('Test cases') {
            steps {
                testCases()
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
