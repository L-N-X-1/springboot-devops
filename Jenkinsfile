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
        SCANNER_IMAGE = "${env.DOCKERHUB_USER}/openscap-scanner"
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
                sh '''
                    mkdir -p reports
                    semgrep scan --config auto --error --json --output reports/semgrep.json .
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/semgrep.json', allowEmptyArchive: true
                }
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
            post {
                always {
                    withCredentials([string(credentialsId: 'sonar-token', variable: 'SONAR_TOKEN')]) {
                        sh '''
                            mkdir -p reports
                            KEY=$(grep '^projectKey=' target/sonar/report-task.txt | cut -d= -f2)
                            curl -s -u "$SONAR_TOKEN:" \
                              "$SONAR_HOST_URL/api/qualitygates/project_status?projectKey=$KEY" \
                              -o reports/sonar-gate.json || true
                        '''
                    }
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
                    trivy config --severity HIGH,CRITICAL --ignorefile .trivyignore.yaml --exit-code 0 \
                      --skip-dirs target --skip-dirs infra \
                      --format template --template @/usr/local/share/trivy/html.tpl \
                      --output reports/trivy-config.html .
                    trivy config --severity HIGH,CRITICAL --ignorefile .trivyignore.yaml --exit-code 0 \
                      --skip-dirs target --skip-dirs infra \
                      --format json --output reports/trivy-config.json .
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

        stage('Build & Push OpenSCAP Scanner') {
            steps {
                withCredentials([usernamePassword(credentialsId: 'dockerhub-creds',
                        usernameVariable: 'DH_USER', passwordVariable: 'DH_TOKEN')]) {
                    sh '''
                        echo "$DH_TOKEN" | docker login -u "$DH_USER" --password-stdin
                        docker build -t $SCANNER_IMAGE:$IMAGE_TAG -t $SCANNER_IMAGE:latest compliance/
                        docker push $SCANNER_IMAGE:$IMAGE_TAG
                        docker push $SCANNER_IMAGE:latest
                    '''
                }
            }
        }

        stage('Deploy to Kubernetes (Ansible)') {
            steps {
                withCredentials([string(credentialsId: 'ansible-vault-pass', variable: 'VAULT_PASS')]) {
                    sh '''
                        set +x
                        umask 077
                        VAULT_FILE=$(mktemp)
                        trap 'rm -f "$VAULT_FILE"' EXIT
                        printf '%s' "$VAULT_PASS" > "$VAULT_FILE"
                        echo "len=$(printf '%s' "$VAULT_PASS" | wc -c)"
                        ansible-playbook -i ansible/inventory.ini ansible/deploy.yml \
                          --vault-password-file "$VAULT_FILE" \
                          -e image=$IMAGE -e tag=$IMAGE_TAG
                        mkdir -p reports
                        { echo "== devops =="; kubectl get pods -n devops -o wide
                          echo; echo "== monitoring =="; kubectl get pods -n monitoring; } > reports/pods.txt || true
                    '''
                }
            }
        }
    }

    post {
        always {
            sh "BUILD_RESULT=${currentBuild.currentResult} python3 scripts/generate-report.py || true"
            archiveArtifacts artifacts: 'reports/pipeline-report.html', allowEmptyArchive: true
            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: 'pipeline-report.html',
                reportName: 'Pipeline Report'
            ])
            sh 'docker logout || true'
            sh 'docker image prune -f || true'
            sh "BUILD_RESULT=${currentBuild.currentResult} DURATION='${currentBuild.durationString}' python3 scripts/generate-report.py || true"
        }
        success {
            echo "Deployed ${IMAGE}:${IMAGE_TAG} to Kubernetes"
        }
    }
}