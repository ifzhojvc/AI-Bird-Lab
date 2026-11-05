FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY central-server ./central-server
RUN dotnet publish central-server/BirdLab.Api.csproj -c Release -o /publish
FROM mcr.microsoft.com/dotnet/aspnet:10.0
WORKDIR /app
COPY --from=build /publish .
COPY data/birds.json /app/data/birds.json
ENV ASPNETCORE_URLS=http://0.0.0.0:5100
ENV CatalogPath=/app/data/birds.json
EXPOSE 5100
ENTRYPOINT ["dotnet", "BirdLab.Api.dll"]
