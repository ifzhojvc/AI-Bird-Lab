set -eu
if [ "$(id -u)" = '0' ]; then
    find /var/lib/rabbitmq \! -user rabbitmq -exec chown rabbitmq '{}' +
    exec gosu rabbitmq /bin/sh "$0" "$@"
fi
rm -f /tmp/bird-rabbitmq-ready
/usr/local/bin/docker-entrypoint.sh rabbitmq-server &
server=$!
trap 'kill -TERM "$server"; wait "$server"' TERM INT
ready=0
for attempt in $(seq 1 60); do
    if rabbitmqctl -q await_startup --timeout 5 >/dev/null 2>&1 && rabbitmq-diagnostics -q check_running >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 2
done
test "$ready" = 1
rabbitmqctl import_definitions /etc/rabbitmq/definitions.json
if ! rabbitmqctl -q list_users | cut -f 1 | grep -Fxq "$RABBITMQ_DEFAULT_USER"; then
    if ! rabbitmqctl add_user "$RABBITMQ_DEFAULT_USER" "$RABBITMQ_DEFAULT_PASS" >/dev/null 2>&1; then
        echo 'RabbitMQ user initialization failed' >&2
        exit 1
    fi
fi
rabbitmqctl set_user_tags "$RABBITMQ_DEFAULT_USER" administrator
rabbitmqctl set_permissions -p birdlab "$RABBITMQ_DEFAULT_USER" '.*' '.*' '.*'
topology_ready=0
for attempt in $(seq 1 30); do
    queues="$(rabbitmqctl -q list_queues -p birdlab name --no-table-headers | grep -c '^bird[.]analysis[.]' || true)"
    bindings="$(rabbitmqctl -q list_bindings -p birdlab source_name --no-table-headers | grep -c '^bird[.]analysis' || true)"
    if [ "$queues" = 9 ] && [ "$bindings" = 9 ]; then
        topology_ready=1
        break
    fi
    sleep 1
done
test "$topology_ready" = 1
touch /tmp/bird-rabbitmq-ready
wait "$server"
