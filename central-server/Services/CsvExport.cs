using System.Globalization;
using System.Text;
using BirdLab.Api.Models;

namespace BirdLab.Api.Services;

public static class CsvExport
{
    public static string Field(string? value)
    {
        value ??= "";
        if (value.TrimStart().FirstOrDefault() is '=' or '+' or '-' or '@' || value.StartsWith('\t') || value.StartsWith('\r')) value = "'" + value;
        return "\"" + value.Replace("\"", "\"\"") + "\"";
    }

    public static byte[] Build(IEnumerable<Analysis> analyses)
    {
        var rows = new StringBuilder("Id,Тип,Файл,Вид,Наукова назва,Confidence,Модель,Ревізія,Дата UTC,Опис\r\n");
        foreach (var a in analyses)
            rows.AppendLine(string.Join(',', new[] { a.Id.ToString(CultureInfo.InvariantCulture), a.AnalysisType, a.OriginalFileName, a.PredictedSpecies, a.Bird?.ScientificName ?? "", a.Confidence.ToString("R", CultureInfo.InvariantCulture), a.ModelName, a.ModelRevision, a.AnalysisDate.ToUniversalTime().ToString("O"), a.Description }.Select(Field)));
        return Encoding.UTF8.GetPreamble().Concat(Encoding.UTF8.GetBytes(rows.ToString())).ToArray();
    }
}
