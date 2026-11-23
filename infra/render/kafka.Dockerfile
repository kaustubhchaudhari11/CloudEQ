FROM apache/kafka:3.9.0
COPY infra/render/kafka-start.sh /opt/kafka/forge-start.sh
CMD ["bash", "/opt/kafka/forge-start.sh"]
