@maxLength(60)
@minLength(2)
@description('Nombre globalmente único para Azure AI Search.')
param searchServiceName string

@allowed([
  'free'
  'basic'
  'standard'
])
param skuName string = 'free'

param location string = resourceGroup().location

// Se despliega de forma independiente del bot para no crear cargos sin una
// decisión explícita. El índice se crea con src/azure_search_ingest.py.
resource searchService 'Microsoft.Search/searchServices@2023-11-01' = {
  name: searchServiceName
  location: location
  sku: {
    name: skuName
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    publicNetworkAccess: 'enabled'
  }
}

output searchEndpoint string = 'https://${searchService.name}.search.windows.net'
