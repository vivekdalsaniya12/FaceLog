pipeline {
    agent { label "worker1" }
    environment {
        GIT_REPO = 'https://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@github.com/vivekdalsaniya12/FaceLog.git' // Replace with your repo URL
        BRANCH = 'master' // Replace with your branch name
    }
    stages {
       stage('Clone Repository') {
            steps {
                git branch: env.BRANCH,
                    url: env.GIT_REPO
            }
        }
        stage('docker-compose-up') {
            steps {
                sh "docker compose up"
            }
        }
    }
}
