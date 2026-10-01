# Jenkins with Maven, Docker CLI, kubectl, Ansible and Semgrep preinstalled
FROM jenkins/jenkins:lts-jdk21

USER root
ENV LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        maven ansible curl ca-certificates gnupg \
        python3 python3-venv python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Semgrep (in its own venv, since Debian blocks system-wide pip installs)
RUN python3 -m venv /opt/semgrep \
    && /opt/semgrep/bin/pip install --no-cache-dir semgrep \
    && ln -s /opt/semgrep/bin/semgrep /usr/local/bin/semgrep

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