pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 15, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10', artifactNumToKeepStr: '10'))
    }

    parameters {
        booleanParam(
            name: 'PUSH_DOCKER_IMAGE',
            defaultValue: true,
            description: 'Push the built Docker image to Docker Hub'
        )
        booleanParam(
            name: 'TAG_LATEST',
            defaultValue: true,
            description: 'Also tag and push :latest (when on main/master or single-branch job)'
        )
    }

    environment {
        IMAGE_REPO         = 'rahuldan98/kubedoctor'
        DOCKERHUB_CRED_ID  = 'dockerhub-credentials'
        HELM_CHART_DIR     = 'helm/kubedoctor'
        HELM_DIST_DIR      = 'dist/helm'
        UV_CACHE_DIR       = "${WORKSPACE}/.cache/uv"
    }

    stages {
        stage('Checkout & Init') {
            steps {
                checkout scm
                script {
                    env.GIT_SHORT_SHA = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()

                    def baseVersion = sh(
                        script: "awk -F': ' '/^version:/ {print \$2}' ${env.HELM_CHART_DIR}/Chart.yaml | tr -d '\"\\r'",
                        returnStdout: true
                    ).trim() ?: '0.1.0'

                    env.IMAGE_TAG         = "${baseVersion}-${env.BUILD_NUMBER}-${env.GIT_SHORT_SHA}"
                    env.CHART_PKG_VERSION = "${baseVersion}-${env.BUILD_NUMBER}"

                    def branch = env.BRANCH_NAME ?: ''
                    env.IS_DEFAULT_BRANCH = (branch == '' || branch == 'main' || branch == 'master') ? 'true' : 'false'
                    env.SHOULD_TAG_LATEST = (params.TAG_LATEST != false && env.IS_DEFAULT_BRANCH == 'true') ? 'true' : 'false'

                    echo "Build metadata -> IMAGE_TAG=${env.IMAGE_TAG}, CHART_PKG_VERSION=${env.CHART_PKG_VERSION}, SHOULD_TAG_LATEST=${env.SHOULD_TAG_LATEST}"
                }
            }
        }

        stage('Tooling Check') {
            steps {
                sh '''
                    set -eu
                    python3 --version
                    uv --version
                    docker --version
                    helm version --short
                '''
            }
        }

        stage('Python Validate & Test') {
            steps {
                sh '''
                    set -eu
                    uv sync --frozen --no-dev
                    uv run --no-sync python -m compileall -q src
                    uv run --no-sync python -c "import kubedoctor, kubedoctor.server, kubedoctor.client; print('KubeDoctor modules imported successfully')"
                    if [ -d tests ]; then
                        uv run pytest
                    else
                        echo "No tests/ directory found; skipping pytest."
                    fi
                '''
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    set -eu
                    docker build -t "${IMAGE_REPO}:${IMAGE_TAG}" .
                    if [ "${SHOULD_TAG_LATEST}" = "true" ]; then
                        docker tag "${IMAGE_REPO}:${IMAGE_TAG}" "${IMAGE_REPO}:latest"
                    fi
                '''
            }
        }

        stage('Docker Push') {
            when {
                expression { return params.PUSH_DOCKER_IMAGE != false }
            }
            steps {
                withCredentials([usernamePassword(
                    credentialsId: env.DOCKERHUB_CRED_ID,
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                        set -eu
                        printf '%s\n' "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                        docker push "${IMAGE_REPO}:${IMAGE_TAG}"
                        if [ "${SHOULD_TAG_LATEST}" = "true" ]; then
                            docker push "${IMAGE_REPO}:latest"
                        fi
                    '''
                }
            }
        }

        stage('Helm Lint & Template') {
            steps {
                sh '''
                    set -eu
                    helm lint "${HELM_CHART_DIR}" --strict
                    helm template kubedoctor "${HELM_CHART_DIR}" \
                        --set "image.repository=${IMAGE_REPO}" \
                        --set "image.tag=${IMAGE_TAG}" > /dev/null
                    helm template kubedoctor "${HELM_CHART_DIR}" \
                        --set "image.repository=${IMAGE_REPO}" \
                        --set "image.tag=${IMAGE_TAG}" \
                        --set "ingress.enabled=true" > /dev/null
                '''
            }
        }

        stage('Helm Package & Archive') {
            steps {
                sh '''
                    set -eu
                    rm -rf "${HELM_DIST_DIR}"
                    mkdir -p "${HELM_DIST_DIR}"
                    helm package "${HELM_CHART_DIR}" \
                        --version "${CHART_PKG_VERSION}" \
                        --app-version "${IMAGE_TAG}" \
                        --destination "${HELM_DIST_DIR}"
                    ls -lh "${HELM_DIST_DIR}"
                '''
                archiveArtifacts(
                    artifacts: "${HELM_DIST_DIR}/*.tgz",
                    fingerprint: true,
                    allowEmptyArchive: false
                )
            }
        }
    }

    post {
        always {
            sh '''
                set +e
                docker logout >/dev/null 2>&1 || true
                if [ -n "${IMAGE_TAG:-}" ]; then
                    docker rmi "${IMAGE_REPO}:${IMAGE_TAG}" >/dev/null 2>&1 || true
                fi
                if [ "${SHOULD_TAG_LATEST:-false}" = "true" ]; then
                    docker rmi "${IMAGE_REPO}:latest" >/dev/null 2>&1 || true
                fi
            '''
        }
        success {
            echo "CI completed. Packaged Helm chart archived from ${HELM_DIST_DIR}/ (image: ${IMAGE_REPO}:${IMAGE_TAG})."
        }
        failure {
            echo "CI failed. Check stage logs for details."
        }
    }
}
