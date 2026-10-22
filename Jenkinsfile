pipeline {
    agent any
    options {
        timestamps()
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
        timeout(time: 30, unit: 'MINUTES')
    }
    environment {
        // Replace with your Docker Hub username/repository.
        IMAGE_REPO = 'ashvinimule9763/jenkins_flask-cicd-docker_projects'
        DOCKERHUB_CREDENTIALS = 'dockerhub-creds'
        APP_CONTAINER = 'jenkins_flask-cicd-docker_projects'
        APP_PORT = '8081'
        CANDIDATE_PORT = '18081'
        IMAGE_TAG = "${BUILD_NUMBER}"
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }
        stage('Unit Tests') {
            steps {
                sh '''
                    set -eu
                    python3 -m venv .venv
                    . .venv/bin/activate
                    python -m pip install --upgrade pip
                    pip install -r requirements-dev.txt
                    pytest -v --junitxml=test-results.xml
                '''
            }
            post {
                always { junit testResults: 'test-results.xml', allowEmptyResults: true }
            }
        }
        stage('Build Docker Image') {
            steps {
                sh '''
                    set -eu
                    docker build --pull \
                      --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" \
                      --label "org.opencontainers.image.version=$IMAGE_TAG" \
                      -t "$IMAGE_REPO:$IMAGE_TAG" .
                    docker image inspect "$IMAGE_REPO:$IMAGE_TAG" >/dev/null
                '''
            }
        }
        stage('Container Smoke Test') {
            steps {
                sh '''
                    set -eu
                    TEST_CONTAINER="flask-ci-test-$BUILD_NUMBER"
                    cleanup() { docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true; }
                    trap cleanup EXIT
                    docker run -d --name "$TEST_CONTAINER" \
                      -e APP_VERSION="$IMAGE_TAG" \
                      -p "127.0.0.1:$CANDIDATE_PORT:5000" \
                      "$IMAGE_REPO:$IMAGE_TAG"
                    ok=0
                    for attempt in $(seq 1 20); do
                      if curl --fail --silent "http://127.0.0.1:$CANDIDATE_PORT/health" >/dev/null; then ok=1; break; fi
                      sleep 2
                    done
                    test "$ok" -eq 1
                    curl --fail --silent "http://127.0.0.1:$CANDIDATE_PORT/" | grep -q '"status":"ok"'
                '''
            }
        }
        stage('Push Image to Docker Hub') {
            steps {
                withCredentials([usernamePassword(credentialsId: "${DOCKERHUB_CREDENTIALS}", usernameVariable: 'DOCKERHUB_USER', passwordVariable: 'DOCKERHUB_TOKEN')]) {
                    sh '''
                        set +x
                        printf '%s' "$DOCKERHUB_TOKEN" | docker login --username "$DOCKERHUB_USER" --password-stdin
                        docker push "$IMAGE_REPO:$IMAGE_TAG"
                        docker logout
                    '''
                }
            }
        }
        stage('Deploy and Verify (with rollback)') {
            steps {
                sh '''
                    set -eu
                    NEW_IMAGE="$IMAGE_REPO:$IMAGE_TAG"
                    OLD_IMAGE=""
                    if docker container inspect "$APP_CONTAINER" >/dev/null 2>&1; then
                      OLD_IMAGE=$(docker inspect --format='{{.Config.Image}}' "$APP_CONTAINER")
                      echo "Previous image: $OLD_IMAGE"
                    else
                      echo "No previous deployment exists; this is the first release."
                    fi
                    docker rm -f "$APP_CONTAINER" >/dev/null 2>&1 || true
                    docker run -d --name "$APP_CONTAINER" --restart unless-stopped \
                      -e APP_VERSION="$IMAGE_TAG" -p "$APP_PORT:5000" "$NEW_IMAGE"
                    healthy=0
                    for attempt in $(seq 1 20); do
                      if curl --fail --silent "http://127.0.0.1:$APP_PORT/health" >/dev/null; then healthy=1; break; fi
                      sleep 2
                    done
                    if [ "$healthy" -eq 1 ]; then
                      if ! curl --fail --silent "http://127.0.0.1:$APP_PORT/" | grep -q "\\"version\\":\\"$IMAGE_TAG\\""; then
                        healthy=0
                      fi
                    fi
                    if [ "$healthy" -eq 1 ]; then
                      echo "Deployment verified: $NEW_IMAGE"
                    else
                      echo "New deployment failed its health check."
                      docker logs "$APP_CONTAINER" || true
                      docker rm -f "$APP_CONTAINER" >/dev/null 2>&1 || true
                      if [ -n "$OLD_IMAGE" ]; then
                        echo "Rolling back to $OLD_IMAGE"
                        docker run -d --name "$APP_CONTAINER" --restart unless-stopped \
                          -e APP_VERSION="rollback" -p "$APP_PORT:5000" "$OLD_IMAGE"
                        rollback_ok=0
                        for attempt in $(seq 1 20); do
                          if curl --fail --silent "http://127.0.0.1:$APP_PORT/health" >/dev/null; then rollback_ok=1; break; fi
                          sleep 2
                        done
                        if [ "$rollback_ok" -ne 1 ]; then echo "CRITICAL: rollback container did not become healthy."; fi
                      else
                        echo "No previous image available to roll back to."
                      fi
                      exit 1
                    fi
                '''
            }
        }
    }
    post {
        success { echo "Build ${BUILD_NUMBER} succeeded and deployment was verified." }
        failure { echo 'Pipeline failed. Review the first failed stage and Console Output.' }
        always {
            sh 'docker image prune -f >/dev/null 2>&1 || true'
            archiveArtifacts artifacts: 'test-results.xml', allowEmptyArchive: true
        }
    }
}
