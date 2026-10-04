#!/bin/bash
set -euo pipefail

BOOTSTRAP_SERVER="${KAFKA_BOOTSTRAP_SERVER:-kafka:29092}"

topics=(
    "quickcommerce.orders"
    "quickcommerce.order_status"
    "quickcommerce.app_events"
)

echo "Waiting for Kafka ($BOOTSTRAP_SERVER)..."

until /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server "$BOOTSTRAP_SERVER" \
    --list >/dev/null 2>&1; do
    sleep 3
done

echo "Kafka is ready."

for topic in "${topics[@]}"; do
    /opt/kafka/bin/kafka-topics.sh \
        --bootstrap-server "$BOOTSTRAP_SERVER" \
        --create \
        --if-not-exists \
        --topic "$topic" \
        --partitions 3 \
        --replication-factor 1

    echo "Topic ready: $topic"
done

echo "All Kafka topics are ready."
