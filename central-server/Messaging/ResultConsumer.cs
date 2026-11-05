using RabbitMQ.Client;
using RabbitMQ.Client.Events;

namespace BirdLab.Api.Messaging;

public sealed class ResultConsumer(RabbitBus bus, IServiceScopeFactory scopes, ILogger<ResultConsumer> logger) : BackgroundService
{
    public bool Listening { get; private set; }

    public static int ReadRetry(object? value) => value switch
    {
        sbyte n => n,
        byte n => n,
        short n => n,
        ushort n => n,
        int n => n,
        long n when n is >= 0 and <= 3 => (int)n,
        _ => -1
    };

    private async Task HandleAsync(IChannel channel, BasicDeliverEventArgs delivery, CancellationToken token)
    {
        var body = delivery.Body.ToArray();
        try
        {
            using var scope = scopes.CreateScope();
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
            deadline.CancelAfter(TimeSpan.FromSeconds(10));
            await scope.ServiceProvider.GetRequiredService<ResultProcessor>().ApplyAsync(body, deadline.Token);
            await channel.BasicAckAsync(delivery.DeliveryTag, false, token);
        }
        catch (InvalidEventException exc)
        {
            logger.LogWarning("Некоректна подія {MessageId}: {Reason}", delivery.BasicProperties.MessageId, exc.Message);
            await channel.BasicRejectAsync(delivery.DeliveryTag, false, token);
        }
        catch (OperationCanceledException) when (token.IsCancellationRequested) { }
        catch (Exception exc)
        {
            logger.LogWarning("Результат {MessageId} не збережено: {Error}", delivery.BasicProperties.MessageId, exc.GetType().Name);
            var retry = 0;
            if (delivery.BasicProperties.Headers?.TryGetValue("x-retry", out var value) == true)
            {
                retry = ReadRetry(value);
                if (retry is < 0 or > 3)
                {
                    await channel.BasicRejectAsync(delivery.DeliveryTag, false, token);
                    return;
                }
            }
            if (retry >= 3)
            {
                await channel.BasicRejectAsync(delivery.DeliveryTag, false, token);
                logger.LogError("Результат {MessageId} у DLQ; потрібне відновлення через replay-results", delivery.BasicProperties.MessageId);
                return;
            }
            try
            {
                await bus.PublishAsync("bird.analysis.retry", $"results.{retry + 1}", body, Guid.TryParse(delivery.BasicProperties.MessageId, out var id) ? id : Guid.NewGuid(), Guid.TryParse(delivery.BasicProperties.CorrelationId, out var correlation) ? correlation : Guid.NewGuid(), token, retry + 1);
                await channel.BasicAckAsync(delivery.DeliveryTag, false, token);
            }
            catch (OperationCanceledException) when (token.IsCancellationRequested) { }
            catch
            {
                await Task.Delay(TimeSpan.FromSeconds(5), token);
                if (channel.IsOpen) await channel.BasicNackAsync(delivery.DeliveryTag, false, true, token);
            }
        }
    }

    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                await using var channel = await (await bus.ConnectAsync(stoppingToken)).CreateChannelAsync(cancellationToken: stoppingToken);
                await RabbitBus.DeclareAsync(channel, stoppingToken);
                await channel.BasicQosAsync(0, 1, false, stoppingToken);
                var closed = new TaskCompletionSource(TaskCreationOptions.RunContinuationsAsynchronously);
                channel.ChannelShutdownAsync += (_, _) => { closed.TrySetResult(); return Task.CompletedTask; };
                var consumer = new AsyncEventingBasicConsumer(channel);
                Task active = Task.CompletedTask;
                consumer.ReceivedAsync += (_, delivery) => active = HandleAsync(channel, delivery, stoppingToken);
                var tag = await channel.BasicConsumeAsync(RabbitBus.Results, false, consumer, stoppingToken);
                Listening = true;
                logger.LogInformation("Consumer результатів слухає {Queue}", RabbitBus.Results);
                try { await closed.Task.WaitAsync(stoppingToken); }
                finally
                {
                    Listening = false;
                    if (channel.IsOpen) await channel.BasicCancelAsync(tag, cancellationToken: CancellationToken.None);
                    try { await active.WaitAsync(TimeSpan.FromSeconds(15)); } catch (Exception) { }
                }
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested) { break; }
            catch (Exception exc) { Listening = false; logger.LogWarning("Consumer перепідключається: {Error}", exc.GetType().Name); }
            try { await Task.Delay(TimeSpan.FromSeconds(5), stoppingToken); }
            catch (OperationCanceledException) { break; }
        }
    }
}
