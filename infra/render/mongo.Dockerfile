FROM mongo:7.0
CMD ["mongod", "--bind_ip_all", "--wiredTigerCacheSizeGB", "0.25"]
