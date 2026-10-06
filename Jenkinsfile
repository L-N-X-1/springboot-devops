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

        stage('Security Scan (Semgrep)') {
            steps {
                sh 'semgrep scan --config auto --error .'
            }
        }

        stage('Trivy FS Scan') {
            steps {
                sh '''
                    mkdir -p reports
                    trivy fs --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore \
                      --format template --template "@/usr/local/share/trivy/html.tpl" --output reports/trivy-fs.html .
                    trivy fs --scanners vuln --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore \
                      --format json --output reports/trivy-fs.json .
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/trivy-fs.html,reports/trivy-fs.json', allowEmptyArchive: true
                    publishHTML(target: [
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'trivy-fs.html',
                        reportName: 'Trivy FS Scan'
                    ])
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

        stage('Trivy Image Scan') {
            steps {
                sh '''
                    mkdir -p reports
                    trivy image --timeout 15m --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore \
                      --format template --template "@/usr/local/share/trivy/html.tpl" --output reports/trivy-image.html $IMAGE:$IMAGE_TAG
                    trivy image --timeout 15m --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore \
                      --format json --output reports/trivy-image.json $IMAGE:$IMAGE_TAG
                    trivy image --timeout 15m --severity HIGH,CRITICAL --ignore-unfixed --ignorefile .trivyignore \
                      --exit-code 1 $IMAGE:$IMAGE_TAG
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/trivy-image.html,reports/trivy-image.json', allowEmptyArchive: true
                    publishHTML(target: [
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'trivy-image.html',
                        reportName: 'Trivy Image Scan'
                    ])
                }
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

        stage('Trivy Config Scan') {
            steps {
                sh '''
                    mkdir -p reports
                    trivy config --severity HIGH,CRITICAL --ignorefile .trivyignore --exit-code 0 \
                      --format template --template "@/usr/local/share/trivy/html.tpl" --output reports/trivy-config.html k8s/ ansible/
                    trivy config --severity HIGH,CRITICAL --ignorefile .trivyignore --exit-code 0 \
                      --format json --output reports/trivy-config.json k8s/ ansible/
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/trivy-config.html,reports/trivy-config.json', allowEmptyArchive: true
                    publishHTML(target: [
                        allowMissing: true,
                        alwaysLinkToLastBuild: true,
                        keepAll: true,
                        reportDir: 'reports',
                        reportFiles: 'trivy-config.html',
                        reportName: 'Trivy Config Scan'
                    ])
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
