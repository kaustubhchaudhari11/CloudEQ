FROM grafana/grafana:11.6.11
USER root
ENV GF_PATHS_PLUGINS=/opt/grafana-plugins
RUN mkdir -p /opt/grafana-plugins \
    && grafana cli --pluginsDir /opt/grafana-plugins plugins install yesoreyeram-infinity-datasource 4.1.6 \
    && chown -R 472:0 /opt/grafana-plugins
COPY infra/grafana/dashboards /var/lib/forge-dashboards
COPY infra/render/grafana-datasource.yaml /etc/grafana/provisioning/datasources/forge.yaml
COPY infra/render/grafana-dashboard.yaml /etc/grafana/provisioning/dashboards/forge.yaml
COPY infra/render/grafana-start.sh /forge-start.sh
USER 472
ENTRYPOINT ["/bin/sh", "/forge-start.sh"]
