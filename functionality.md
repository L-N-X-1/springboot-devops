# Spring Boot DevOps — Operating Guide

Everything you need for day-to-day use, written for someone new to DevOps.

---

## 1. The big picture

There are **two separate worlds** in this project:

**The factory** (Docker Compose, on your machine) — builds and checks the app:

| Tool | Job |
|---|---|
| Jenkins | The boss. Runs all the steps in order. |
| SonarQube | Inspects code quality. Can fail the build. |
| Nexus | Warehouse for the built JAR files. |

**The production environment** (Kubernetes / Minikube) — runs the finished app:

| Tool | Job |
|---|---|
| Kubernetes | Runs the app, restarts it if it crashes, handles updates. |
| Prometheus | Collects numbers from the app every 15 seconds. |
| Grafana | Draws graphs from those numbers. |

The factory builds the app, ships it to DockerHub, and Ansible tells Kubernetes to run the new version.

```
you: git push
   ↓
GitHub → Jenkins ─┬→ Maven      build + run tests
                  ├→ SonarQube  quality gate (fails build if bad)
                  ├→ Nexus      store the JAR
                  ├→ Docker     build image
                  ├→ DockerHub  push image
                  └→ Ansible    deploy to Kubernetes
                                    ↓
                            app running in 2 pods
                            Prometheus scrapes it → Grafana shows it
```

---

## 2. Daily on / off

**Turn on** — Minikube first, always (Jenkins attaches to its network):
```bash
minikube start
./infra/export-kubeconfig.sh
cd infra && docker compose up -d
```
Wait ~2 minutes for SonarQube and Nexus to finish booting.

**Turn off:**
```bash
cd infra && docker compose down
minikube stop
```

**Check everything is alive:**
```bash
docker ps                    # jenkins, sonarqube, nexus → Up
kubectl get pods -A          # springboot-app, prometheus, grafana → Running
```

### Never run these by accident

| Command | What it destroys |
|---|---|
| `docker compose down -v` | All Jenkins jobs, SonarQube history, Nexus JARs, the accepted EULA |
| `minikube delete` | The whole cluster: app, Prometheus, Grafana |

Plain `down` and `stop` are safe. The `-v` and `delete` are the dangerous ones.

---

## 3. Your URLs

The factory runs on localhost. The cluster is behind the Minikube IP.

```bash
echo "Jenkins:    http://localhost:8080"        # admin / admin123
echo "SonarQube:  http://localhost:9000"
echo "Nexus:      http://localhost:8081"
echo "App:        http://$(minikube ip):30080"
echo "Prometheus: http://$(minikube ip):30090"
echo "Grafana:    http://$(minikube ip):30030"  # admin / admin
```

Save that as a habit — the Minikube IP can change after a restart.

If a cluster URL won't load, forward it to localhost instead (keep the terminal open):
```bash
kubectl port-forward -n monitoring svc/grafana 3000:3000
```

---

## 4. The normal workflow

This is the whole point of the project: **you only ever push code.**

```bash
# 1. edit some code
# 2. commit and push
git add .
git commit -m "what I changed"
git push
```

Jenkins notices within ~2 minutes and does the rest. Open Jenkins and watch the Stage View fill in.

**Where to look while it runs:**

| Stage | Where to verify it worked |
|---|---|
| Build & Test | Jenkins → build → Test Result |
| SonarQube | localhost:9000 → new analysis date |
| Nexus | localhost:8081 → Browse → maven-snapshots |
| DockerHub | hub.docker.com → a new tag = build number |
| Deploy | `kubectl get pods -n devops` → new pods appear |

**Confirm the new version is live:**
```bash
curl http://$(minikube ip):30080/
```

---

## 5. Trying things out

**Watch a deploy happen live** (run before pushing, `Ctrl+C` to quit):
```bash
kubectl get pods -n devops -w
```
You'll see new pods start and old ones terminate one at a time. That's a rolling update: the app never goes fully down.

**Which image version is running right now:**
```bash
kubectl get deploy springboot-app -n devops -o jsonpath='{..image}'; echo
```

**Prove the quality gates work.** Break a test on purpose and push. The pipeline fails at Build & Test, nothing deploys, and the old version keeps serving traffic. Fix it and push again.

**Prove self-healing works.** Kill a pod and watch Kubernetes replace it:
```bash
kubectl delete pod -n devops -l app=springboot-app --field-selector status.phase=Running
kubectl get pods -n devops -w
```

**Roll back to the previous version:**
```bash
kubectl rollout undo deployment/springboot-app -n devops
```

**Scale up:**
```bash
kubectl scale deploy/springboot-app -n devops --replicas=4
```
Note: the next pipeline run resets this to 2, because the manifest says 2. That's infrastructure-as-code doing its job — the file is the truth, not your manual change.

**Make the graphs move:**
```bash
for i in $(seq 500); do curl -s http://$(minikube ip):30080/api/products > /dev/null; done
```
Then open Grafana → Dashboards → Spring Boot App.

---

## 6. Everyday commands

```bash
# Kubernetes — your main tool
kubectl get pods -n devops                        # is the app healthy?
kubectl logs -f deploy/springboot-app -n devops   # app logs, live
kubectl describe pod <pod-name> -n devops         # why is this pod unhappy?
kubectl rollout status deploy/springboot-app -n devops
kubectl rollout undo deploy/springboot-app -n devops

# The factory
docker ps                     # what's running
docker logs -f jenkins        # Jenkins logs
docker compose restart jenkins

# Running the app locally, no cluster involved
mvn spring-boot:run           # http://localhost:8082 if Jenkins has 8080
mvn clean verify              # build + tests + coverage report
```

`kubectl describe` is the command to reach for when something's wrong. The **Events** section at the bottom usually says exactly what failed.

---

## 7. Changing things

| To change | Edit | Then |
|---|---|---|
| The app | `src/` | `git push` |
| Pipeline steps | `Jenkinsfile` | `git push` |
| Replica count, CPU/memory, health checks | `k8s/app/deployment.yaml.j2` | `git push` |
| What gets deployed | `ansible/deploy.yml` | `git push` |
| Prometheus config | `k8s/monitoring/prometheus.yaml` | `kubectl apply -f k8s/monitoring/` |
| Passwords, tokens, DockerHub user | `infra/.env` | `cd infra && docker compose up -d --force-recreate jenkins` |
| Jenkins plugins | `infra/jenkins/Dockerfile` | `docker compose up -d --build jenkins` |

Rule of thumb: **anything in Git changes through a push.** Anything in `infra/` is local setup and needs a container restart.

---

## 8. When something breaks

Work through it in this order:

1. **Read the Jenkins Console Output.** Scroll to the bottom. The real error is usually a few lines above `BUILD FAILURE`.
2. **Find which stage failed** in the Stage View — that tells you which tool to investigate.
3. **If it's the deploy stage,** check the cluster: `kubectl get pods -n devops` then `kubectl describe pod <name> -n devops`.

| Symptom | Cause | Fix |
|---|---|---|
| Deploy stage can't reach the cluster | Minikube IP changed after restart | `./infra/export-kubeconfig.sh` then `docker compose restart jenkins` |
| `network minikube not found` | Compose started before Minikube | `minikube start`, then `docker compose up -d` |
| Nexus `403 Forbidden` | EULA not accepted | Accept it at localhost:8081, once per Nexus install |
| Nexus `401` | Wrong password in `.env` | Fix it, then `docker compose up -d --force-recreate jenkins` |
| `ImagePullBackOff` | DockerHub repo is private, or wrong username | Make the repo public; check `DOCKERHUB_USER` |
| `CrashLoopBackOff` | App itself is failing to start | `kubectl logs <pod> -n devops` |
| Pod stuck `Pending` | Cluster out of RAM | `minikube stop`, restart with `--memory=6144` |
| SonarQube stage fails | Quality gate failed | Open the project in SonarQube; it lists the failed condition |
| Jenkins can't clone from GitHub | Repo is private | Make it public, or add GitHub credentials |
| Everything is slow / OOM | Not enough RAM | Close other apps; you need ~10 GB free |

**Useful full-picture command when you're lost:**
```bash
kubectl get all -A | grep -v kube-system
```

---

## 9. Quick vocabulary

| Word | Meaning |
|---|---|
| **Pod** | One running copy of your app. You have 2. |
| **Deployment** | The recipe saying "keep 2 pods of this image alive". |
| **Service** | A stable address for the pods, since pods come and go. |
| **NodePort** | A port on the cluster that lets you reach a Service from outside — 30080, 30090, 30030 here. |
| **Namespace** | A folder to group things — `devops` for the app, `monitoring` for Prometheus/Grafana. |
| **Image** | A frozen snapshot of your app, built by Docker, stored in DockerHub. |
| **Tag** | The version label on an image — here it's the Jenkins build number. |
| **Rolling update** | Replacing pods one at a time so the app never goes down. |
| **Quality gate** | SonarQube's pass/fail rule set. |
| **Artifact** | The built JAR file, stored in Nexus. |
| **Pipeline** | The series of stages in the `Jenkinsfile`. |
| **Manifest** | A YAML file describing something you want in Kubernetes. |
| **Probe** | A health check Kubernetes runs against the app. Liveness = restart if dead. Readiness = don't send traffic yet. |

---

## 10. The API

Base URL: `http://$(minikube ip):30080`

| Method | Path | Body |
|---|---|---|
| GET | `/` | – |
| GET | `/api/products` | – |
| GET | `/api/products/{id}` | – |
| POST | `/api/products` | `{"name":"Mouse","price":25.5}` |
| PUT | `/api/products/{id}` | `{"name":"Mouse","price":30}` |
| DELETE | `/api/products/{id}` | – |
| GET | `/actuator/health` | – |
| GET | `/actuator/prometheus` | raw metrics |

```bash
URL=http://$(minikube ip):30080
curl $URL/api/products
curl -X POST $URL/api/products -H 'Content-Type: application/json' -d '{"name":"Mouse","price":25.5}'
```

Note: the app uses an in-memory database, so products you add disappear when a pod restarts. That's intentional for a lab.

---

## 11. Full reset (last resort)

Only if things are badly broken. This wipes all history and you'll redo the token setup:

```bash
cd infra && docker compose down -v
minikube delete
minikube start --driver=docker --memory=4096
./infra/export-kubeconfig.sh
docker compose up -d
```
Then redo: SonarQube password + token, Nexus password + EULA, update `.env`, recreate Jenkins, and run one build.
