FROM grafana/grafana:11.6.11
USER root
RUN grafana cli plugins install yesoreyeram-infinity-datasource 4.1.6
COPY infra/grafana/dashboards /var/lib/forge-dashboards
COPY infra/render/grafana-datasource.yaml /etc/grafana/provisioning/datasources/forge.yaml
COPY infra/render/grafana-dashboard.yaml /etc/grafana/provisioning/dashboards/forge.yaml
COPY infra/render/grafana-start.sh /forge-start.sh
USER 472
ENTRYPOINT ["/bin/sh", "/forge-start.sh"]
