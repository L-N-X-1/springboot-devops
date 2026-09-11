pipeline {
    agent any

    triggers {
        githubPush()            // instant build when a GitHub webhook is configured
        pollSCM('H/2 * * * *')  // fallback: check GitHub for new commits every ~2 min
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        disableConcurrentBuilds()
    }

    environment {
        // DOCKERHUB_USER, SONAR_HOST_URL and NEXUS_URL are global vars set in infra/jenkins/casc.yaml
        IMAGE     = "${env.DOCKERHUB_USER}/springboot-devops"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Build & Test (Maven)') {
            steps {
                sh 'mvn -B clean verify'
            }
            post {
                always {
                    junit testResults: 'target/surefire-reports/*.xml', allowEmptyResults: true
                }
            }
        }

        stage('Code Quality (SonarQube)') {
            steps {
                withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                    // qualitygate.wait=true -> the build FAILS if the quality gate fails
                    sh '''
                        mvn -B sonar:sonar \
                          -Dsonar.host.url=$SONAR_HOST_URL \
                          -Dsonar.token=$SONAR_TOKEN \
                          -Dsonar.qualitygate.wait=true
                    '''
                }
            }
        }

        stage('Publish Artifact (Nexus)') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'nexus-creds',
                        usernameVariable: 'NEXUS_USER', passwordVariable: 'NEXUS_PASS')]) {
                    sh 'mvn -B deploy -DskipTests -s ci/maven-settings.xml -Dnexus.url=$NEXUS_URL'
                }
            }
        }

        stage('Build Image (Docker)') {
            steps {
                sh 'docker build -t $IMAGE:$IMAGE_TAG -t $IMAGE:latest .'
            }
        }

        stage('Push Image (DockerHub)') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        docker push $IMAGE:$IMAGE_TAG
                        docker push $IMAGE:latest
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes (Ansible)') {
            steps {
                sh 'ansible-playbook -i ansible/inventory.ini ansible/deploy.yml -e image=$IMAGE -e tag=$IMAGE_TAG'
            }
        }
    }

    post {
        always {
            sh 'docker logout || true'
            sh 'docker image prune -f || true'
        }
        success {
            echo "Deployed ${IMAGE}:${IMAGE_TAG} to Kubernetes"
        }
    }
}
