FROM debian:12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openscap-scanner python3 python3-defusedxml ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY ssg-debian12-ds.xml /opt/ssg/ssg-debian12-ds.xml
COPY scan.sh summarize.py /usr/local/bin/
RUN chmod +x /usr/local/bin/scan.sh
# Runs as root on purpose: the scanner must read root-only files of the node mounted at /host.
# nosemgrep: dockerfile.security.missing-user-entrypoint.missing-user-entrypoint
ENTRYPOINT ["/usr/local/bin/scan.sh"]