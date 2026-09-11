# Jenkins with Maven, Docker CLI, kubectl and Ansible preinstalled
FROM jenkins/jenkins:lts-jdk21

USER root
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        maven ansible curl ca-certificates gnupg \
    && rm -rf /var/lib/apt/lists/*

# Docker CLI (talks to the host Docker daemon through the mounted socket)
RUN install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-buildx-plugin \
    && rm -rf /var/lib/apt/lists/*

# kubectl
RUN curl -fsSLo /usr/local/bin/kubectl \
        "https://dl.k8s.io/release/$(curl -fsSL https://dl.k8s.io/release/stable.txt)/bin/linux/$(dpkg --print-architecture)/kubectl" \
    && chmod +x /usr/local/bin/kubectl

USER jenkins

# Plugins (Configuration-as-Code sets up users, credentials and the pipeline job automatically)
RUN jenkins-plugin-cli --plugins \
        configuration-as-code \
        job-dsl \
        workflow-aggregator \
        git \
        github \
        credentials-binding \
        junit \
        pipeline-stage-view
