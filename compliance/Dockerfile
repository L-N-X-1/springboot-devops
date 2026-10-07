FROM debian:12-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends openscap-scanner python3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY ssg-debian12-ds.xml /opt/ssg/ssg-debian12-ds.xml
COPY scan.sh summarize.py /usr/local/bin/
RUN chmod +x /usr/local/bin/scan.sh
ENTRYPOINT ["/usr/local/bin/scan.sh"]
