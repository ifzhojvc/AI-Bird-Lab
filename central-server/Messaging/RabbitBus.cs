using RabbitMQ.Client;

namespace BirdLab.Api.Messaging;

public interface IEventPublisher
{
    Task PublishAsync(string exchange, string routingKey, ReadOnlyMemory<byte> body, Guid eventId, Guid correlationId, CancellationToken token, int retry = 0);
}

public sealed class RabbitBus(IConfiguration configuration, ILogger<RabbitBus> logger) : IEventPublisher, IAsyncDisposable
{
    private readonly SemaphoreSlim connectionGate = new(1, 1);
    private readonly SemaphoreSlim publishGate = new(1, 1);
    private IConnection? connection;
    private IChannel? publisher;
    public uint WorkerConsumers { get; private set; }
    public const string Exchange = "bird.analysis";
    public const string Requests = "bird.analysis.requests";
    public const string Results = "bird.analysis.results";

    public async Task<IConnection> ConnectAsync(CancellationToken token)
    {
        await connectionGate.WaitAsync(token);
        try
        {
            if (connection is { IsOpen: true }) return connection;
            if (connection is not null) await connection.DisposeAsync();
            var password = configuration["RabbitMQ:Password"];
            var user = configuration["RabbitMQ:Username"] ?? "birdlab";
            if (string.IsNullOrWhiteSpace(password) || user == "guest") throw new InvalidOperationException("Налаштуйте окремі RabbitMQ:Username та RabbitMQ:Password.");
            var factory = new ConnectionFactory
            {
                HostName = configuration["RabbitMQ:Host"] ?? "127.0.0.1",
                Port = configuration.GetValue("RabbitMQ:Port", 5672),
                VirtualHost = configuration["RabbitMQ:VirtualHost"] ?? "birdlab", UserName = user, Password = password,
                AutomaticRecoveryEnabled = false,
                RequestedHeartbeat = TimeSpan.FromSeconds(20),
                RequestedConnectionTimeout = TimeSpan.FromSeconds(5),
                ClientProvidedName = "birdlab-central"
            };
            connection = await factory.CreateConnectionAsync(token);
            logger.LogInformation("Підключено до RabbitMQ");
            return connection;
        }
        finally { connectionGate.Release(); }
    }

    public static async Task DeclareAsync(IChannel channel, CancellationToken token)
    {
        await channel.ExchangeDeclareAsync(Exchange, ExchangeType.Direct, durable: true, cancellationToken: token);
        await channel.ExchangeDeclareAsync("bird.analysis.retry", ExchangeType.Direct, durable: true, cancellationToken: token);
        await channel.ExchangeDeclareAsync("bird.analysis.dlx", ExchangeType.Direct, durable: true, cancellationToken: token);
        foreach (var name in new[] { Requests, Results, "bird.analysis.dead" })
        {
            await channel.QueueDeclareAsync(name, durable: true, exclusive: false, autoDelete: false, arguments: new Dictionary<string, object?> { ["x-queue-type"] = "quorum" }, cancellationToken: token);
            await channel.QueueBindAsync(name, name.EndsWith("dead") ? "bird.analysis.dlx" : Exchange, name.EndsWith("dead") ? "analysis.dead" : name.EndsWith("requests") ? "analysis.requested" : "analysis.event", cancellationToken: token);
        }
        foreach (var kind in new[] { "requests", "results" })
        for (var n = 1; n <= 3; n++)
        {
            var name = $"bird.analysis.{kind}.retry.{n}";
            await channel.QueueDeclareAsync(name, durable: true, exclusive: false, autoDelete: false, arguments: new Dictionary<string, object?> { ["x-queue-type"] = "quorum" }, cancellationToken: token);
            await channel.QueueBindAsync(name, "bird.analysis.retry", $"{kind}.{n}", cancellationToken: token);
        }
    }

    public async Task PublishAsync(string exchange, string routingKey, ReadOnlyMemory<byte> body, Guid eventId, Guid correlationId, CancellationToken token, int retry = 0)
    {
        await publishGate.WaitAsync(token);
        try
        {
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
            deadline.CancelAfter(TimeSpan.FromSeconds(10));
            if (publisher is not { IsOpen: true })
            {
                if (publisher is not null) await publisher.DisposeAsync();
                publisher = await (await ConnectAsync(deadline.Token)).CreateChannelAsync(new CreateChannelOptions(true, true), deadline.Token);
                await DeclareAsync(publisher, deadline.Token);
            }
            var properties = new BasicProperties { Persistent = true, ContentType = "application/json", MessageId = eventId.ToString(), CorrelationId = correlationId.ToString(), Headers = new Dictionary<string, object?> { ["x-retry"] = retry } };
            await publisher.BasicPublishAsync(exchange, routingKey, mandatory: true, basicProperties: properties, body: body, cancellationToken: deadline.Token);
        }
        catch
        {
            if (publisher is not null) await publisher.DisposeAsync();
            publisher = null;
            throw;
        }
        finally { publishGate.Release(); }
    }

    public async Task<bool> ProbeAsync(CancellationToken token)
    {
        try
        {
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
            deadline.CancelAfter(TimeSpan.FromSeconds(3));
            await using var channel = await (await ConnectAsync(deadline.Token)).CreateChannelAsync(cancellationToken: deadline.Token);
            var requests = await channel.QueueDeclarePassiveAsync(Requests, deadline.Token);
            WorkerConsumers = requests.ConsumerCount;
            await channel.QueueDeclarePassiveAsync(Results, deadline.Token);
            return true;
        }
        catch { WorkerConsumers = 0; return false; }
    }

    public async ValueTask DisposeAsync()
    {
        if (publisher is not null) await publisher.DisposeAsync();
        if (connection is not null) await connection.DisposeAsync();
        connectionGate.Dispose();
        publishGate.Dispose();
    }
}
