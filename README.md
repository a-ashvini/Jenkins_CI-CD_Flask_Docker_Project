# Interview Project: End-to-End Jenkins CI/CD for Python Flask

GitHub push webhook -> Jenkins declarative Jenkinsfile -> Python unit tests -> Docker build -> container smoke test -> Docker Hub push -> EC2 deployment -> HTTP health verification -> rollback to the previous image if the new deployment is unhealthy.

This is an interview/lab implementation. Jenkins and the app share one EC2 host as requested. Production systems should normally isolate Jenkins from deployment hosts and use controlled deployment permissions.

## Files

* `app.py`: Flask app with `/` and `/health` endpoints
* `test\_app.py`: pytest unit tests
* `requirements.txt`, `requirements-dev.txt`: runtime and test dependencies
* `Dockerfile`: non-root runtime image and Docker health check
* `Jenkinsfile`: pipeline, versioned image, push, deploy, verification, rollback

## 1\. Prerequisites

Install/configure Jenkins, Git, Docker Engine, Python 3 with venv support, and curl on the EC2 host. Install Jenkins Pipeline, Git, GitHub integration/webhook support, Credentials Binding, and JUnit plugins.

Verify:

```bash
docker --version
git --version
python3 --version
python3 -m venv --help
curl --version
sudo -u jenkins docker ps
```

If the last command fails, fix Docker access for the Jenkins agent and restart Jenkins. Membership in the Docker group is effectively root-level access. Never expose the Docker daemon on an unauthenticated TCP port.

## 2\. Docker Hub and Jenkins credentials

1. Create a Docker Hub repository named `flask-cicd-interview`.
2. Create a Docker Hub access token.
3. Jenkins -> Manage Jenkins -> Credentials -> System -> Global credentials -> Add Credentials.
4. Kind: `Username with password`; username = Docker Hub username; password = access token; ID = `dockerhub-creds`.
5. Edit `Jenkinsfile` and replace `YOUR\_DOCKERHUB\_USERNAME` in `IMAGE\_REPO` with your username.
Never commit secrets or print them in logs.

## 3\. Push to GitHub

Create a new repository, e.g. `Jenkins\_CI-CD\_Flask\_Docker\_Project`, then run these commands from this folder:

```bash
git init
git add .
git commit -m "Add Flask CI/CD pipeline"
git branch -M main
git remote add origin https://github.com/YOUR\_GITHUB\_USERNAME/Jenkins\_CI-CD\_Flask\_Docker\_Project.git

git push -u origin main
```

Replace the sample URL. Keep your existing `Jenkins\_cicd\_project` safe; use a new repository or branch unless you intentionally want to replace it.

## 4\. Create Jenkins Pipeline job

1. Jenkins Dashboard -> New Item -> `flask-cicd-pipeline` -> Pipeline -> OK.
2. Build Triggers: select `GitHub hook trigger for GITScm polling`.
3. Pipeline -> Definition: `Pipeline script from SCM`.
4. SCM: Git; Repository URL: your repo; Branch Specifier: `\*/main`; Script Path: `Jenkinsfile`.
5. Save and click Build Now.
For private GitHub repositories, configure credentials with read access.

## 5\. GitHub webhook

Repository -> Settings -> Webhooks -> Add webhook:

* Payload URL: `https://YOUR\_JENKINS\_HTTPS\_HOST/github-webhook/` (recommended)
* Content type: `application/json`
* Event: Just the push event
* Active: enabled
A temporary lab may use `http://YOUR\_EC2\_PUBLIC\_IP:8080/github-webhook/`, but do not leave Jenkins publicly exposed over plain HTTP. Prefer HTTPS, restrict Jenkins to your IP/VPN, and validate a webhook secret if supported. Check Recent Deliveries and Jenkins Build History.

## 6\. Security group

* SSH 22: your IP only
* Jenkins 8080: your IP/VPN only, preferably behind HTTPS
* App 8081: your IP only for demo
Do not open these ports to everyone without a deliberate protected design.

## 7\. Test it

1. Run the first Jenkins build.
2. Visit `http://YOUR\_EC2\_PUBLIC\_IP:8081/` and `/health`.
3. Change `app.py`, then:

```bash
git add app.py
git commit -m "Change Flask response"
git push
```

4. Confirm a new build starts automatically and `/` returns the new build version.
5. Intentionally change a test expectation and push: Unit Tests should fail and deployment should not run. Revert the test change after demonstrating this.
6. Test rollback only in a disposable lab; never force a failure on a production workload.

## 8\. Troubleshooting

```bash
docker ps
docker logs flask-cicd-app
docker inspect flask-cicd-app
curl -i http://127.0.0.1:8081/health
curl -i http://127.0.0.1:8081/
```

* Docker permission denied: Jenkins agent cannot access Docker.
* `venv` missing: install your OS Python venv package.
* Docker push denied: check repository, token, and credential ID.
* Port in use: change `APP\_PORT` and the matching security-group rule.
* Webhook delivered but no build: check trigger, URL, branch, and recent delivery.
* Health check fails: inspect container logs, port mapping, and endpoint.

## Interview explanation

"I created a declarative Jenkins pipeline for a Python Flask application. A GitHub webhook triggers Jenkins on every push. Jenkins checks out the code, runs pytest unit tests, builds a versioned Docker image, smoke-tests the container, and pushes it to Docker Hub using credentials stored in Jenkins. It then deploys the image on EC2, checks the health endpoint, and attempts to restore the previous image if the new deployment fails its health check. I also tested a failing unit test to confirm a bad change is stopped before deployment."

Only claim steps you personally ran and verified. For production, add separate build/deployment permissions, HTTPS, image scanning, retention policy, and a thoroughly tested rollback strategy.

