# Spring Boot DevOps Project

A small Product REST API with a complete CI/CD pipeline.

```
git push → GitHub → Jenkins → Maven (build + test) → SonarQube (quality gate)
        → Nexus (JAR) → Docker build → DockerHub → Ansible → Kubernetes (Minikube)
        → Prometheus scrapes metrics → Grafana dashboard
```

## Project layout

```
├── src/                     Spring Boot app (Product CRUD + Actuator metrics)
├── pom.xml                  Maven build, JaCoCo, SonarQube, Nexus config
├── Dockerfile               Multi-stage image build
├── Jenkinsfile              The CI/CD pipeline
├── ci/maven-settings.xml    Nexus credentials (injected by Jenkins)
├── ansible/                 Playbook that deploys to Kubernetes
├── k8s/app/                 App Deployment + Service
├── k8s/monitoring/          Prometheus + Grafana (with a ready dashboard)
└── infra/                   Docker Compose for Jenkins, SonarQube, Nexus
```

## Prerequisites

Docker (Desktop), Minikube, Git, a GitHub account, a DockerHub account, and ~10 GB free RAM.
On Windows, run the commands in **Git Bash** or **WSL**.

---

## Setup (one time)

**1. Push the code to GitHub** (create an empty **public** repo named `springboot-devops` first)
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USER/springboot-devops.git
git push -u origin main
```

**2. Start Kubernetes** (must be started before Jenkins)
```bash
minikube start --driver=docker --cpus=2 --memory=4096
./infra/export-kubeconfig.sh      # lets Jenkins talk to Minikube
```

**3. Create your config**
```bash
cd infra
cp .env.example .env              # fill GIT_REPO_URL, DOCKERHUB_USER, DOCKERHUB_TOKEN
```
DockerHub token: hub.docker.com → Account settings → Personal access tokens (Read & Write).

**4. Start SonarQube and Nexus** (wait ~2 min for them to boot)
```bash
docker compose up -d sonarqube nexus
```
- **SonarQube** → http://localhost:9000, login `admin/admin`, set a new password.
  Then *My Account → Security → Generate Token* (type: Global Analysis) → put it in `SONAR_TOKEN`.
- **Nexus** → get the first password: `docker exec nexus cat /nexus-data/admin.password`
  Log in at http://localhost:8081 as `admin`, set a new password → put it in `NEXUS_PASSWORD`.

**5. Start Jenkins**
```bash
docker compose up -d --build jenkins
```
Open http://localhost:8080 (login from `.env`, default `admin/admin123`).
The job **springboot-devops** and all credentials are created automatically.
Click **Build Now** once. After that, every `git push` triggers a build (checked every 2 min).

**6. Open the app and monitoring**
```bash
minikube service springboot-app -n devops --url    # the API
minikube service prometheus -n monitoring --url    # Prometheus
minikube service grafana -n monitoring --url       # Grafana (admin/admin)
```

---

## How to use / manage each tool

### Git & GitHub
```bash
git checkout -b feature/x        # new branch
git add . && git commit -m "msg"
git push                         # on main → Jenkins builds & deploys
```
Optional instant builds: expose Jenkins with `ngrok http 8080`, then in GitHub repo
*Settings → Webhooks* add `https://<ngrok-url>/github-webhook/` (content type `application/json`).

### Maven
```bash
mvn spring-boot:run              # run locally → http://localhost:8080
mvn test                         # unit tests
mvn clean verify                 # build + tests + coverage (target/site/jacoco/index.html)
mvn package                      # JAR → target/app.jar
```

### Jenkins — http://localhost:8080
- **Run a build:** job → *Build Now*. **Logs:** build number → *Console Output*.
- **Change pipeline:** edit `Jenkinsfile`, commit, push.
- **Change credentials:** edit `infra/.env` then `docker compose up -d jenkins` (config is reapplied on start).
- **Add plugins:** add to `infra/jenkins/Dockerfile`, then `docker compose up -d --build jenkins`.
- Logs: `docker logs -f jenkins`

### SonarQube — http://localhost:9000
- *Projects → springboot-devops*: bugs, code smells, coverage, duplications.
- *Quality Gates*: the rules a build must pass. If the gate fails, the Jenkins build fails.
- To relax rules: create your own gate, then set it on the project (*Project Settings → Quality Gate*).

### Nexus — http://localhost:8081
- *Browse → maven-snapshots → com/example/springboot-devops*: every build's JAR.
- Current version is `1.0.0-SNAPSHOT`. For a release, change `<version>` in `pom.xml` to `1.0.0` (goes to `maven-releases`, which can't be overwritten).

### Docker
```bash
docker build -t springboot-devops .
docker run -p 8080:8080 springboot-devops
docker images        # list images
docker ps            # running containers
```

### DockerHub — hub.docker.com
Jenkins pushes `YOUR_USER/springboot-devops:<build-number>` and `:latest`.
Keep the repo **public** so Minikube can pull it. Any tag can be pulled with `docker pull YOUR_USER/springboot-devops:12`.

### Kubernetes (Minikube)
```bash
kubectl get all -n devops                                   # everything for the app
kubectl logs -f deploy/springboot-app -n devops             # app logs
kubectl describe pod <pod> -n devops                        # debug a pod
kubectl scale deploy/springboot-app --replicas=3 -n devops  # scale
kubectl rollout history deploy/springboot-app -n devops     # deploy history
kubectl rollout undo deploy/springboot-app -n devops        # rollback
minikube dashboard                                          # web UI
minikube stop / minikube start                              # stop / resume cluster
```

### Ansible
Jenkins runs it for you. To deploy a specific version by hand (from the project root):
```bash
ansible-playbook -i ansible/inventory.ini ansible/deploy.yml \
  -e image=YOUR_USER/springboot-devops -e tag=12
```
Change what gets deployed in `ansible/deploy.yml` and the manifests in `k8s/`.

### Prometheus
- *Status → Targets*: both app pods should be **UP**.
- Try queries in *Graph*:
  - `http_server_requests_seconds_count`
  - `jvm_memory_used_bytes{area="heap"}`
  - `rate(http_server_requests_seconds_count[1m])`
- Config: `k8s/monitoring/prometheus.yaml`. Any pod with the `prometheus.io/scrape: "true"` annotation is scraped automatically.

### Grafana
- Login `admin/admin` → *Dashboards → Spring Boot App* (pods, req/s, latency, heap, CPU).
- More JVM detail: *Dashboards → New → Import* → ID `4701` → choose the Prometheus datasource.
- Generate some traffic to see graphs move:
  ```bash
  URL=$(minikube service springboot-app -n devops --url)
  for i in $(seq 200); do curl -s $URL/api/products > /dev/null; done
  ```

---

## API

| Method | URL | Body |
|---|---|---|
| GET | `/` | – |
| GET | `/api/products` | – |
| GET | `/api/products/{id}` | – |
| POST | `/api/products` | `{"name":"Mouse","price":25.5}` |
| PUT | `/api/products/{id}` | `{"name":"Mouse","price":30}` |
| DELETE | `/api/products/{id}` | – |
| GET | `/actuator/health`, `/actuator/prometheus` | – |

## Stop everything
```bash
cd infra && docker compose down        # add -v to also delete all data
minikube stop
```

## Troubleshooting

| Problem | Fix |
|---|---|
| Deploy stage can't reach cluster | Minikube IP changed: `./infra/export-kubeconfig.sh` then `docker compose restart jenkins` |
| `network minikube not found` | Start Minikube before `docker compose up` |
| `kubeconfig` is a folder | You started Jenkins before step 2: `rm -rf infra/jenkins/kubeconfig`, rerun the script, restart Jenkins |
| Nexus `401` | Wrong `NEXUS_PASSWORD` in `.env` → fix, then `docker compose up -d jenkins` |
| SonarQube stage fails | Open the project in SonarQube to see which quality gate condition failed |
| `ImagePullBackOff` | DockerHub repo must be public and `DOCKERHUB_USER` correct |
| SonarQube won't start (Linux) | `sudo sysctl -w vm.max_map_count=524288` |
