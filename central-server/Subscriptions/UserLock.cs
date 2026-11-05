using BirdLab.Api.Data;
using Microsoft.EntityFrameworkCore;

namespace BirdLab.Api.Subscriptions;

public static class UserLock
{
    public static async Task AcquireAsync(BirdDbContext db, string userId, CancellationToken token)
    {
        if (!db.Database.IsSqlServer()) return;
        if (db.Database.CurrentTransaction is null) throw new InvalidOperationException("User lock requires a SQL transaction.");
        var resource = "birdlab:user:" + userId;
        await db.Database.ExecuteSqlInterpolatedAsync($"DECLARE @result int; EXEC @result = sys.sp_getapplock @Resource={resource}, @LockMode='Exclusive', @LockOwner='Transaction', @LockTimeout=10000; IF @result < 0 THROW 51000, 'User lock unavailable', 1;", token);
    }
}
