// Foundry environment for the "Why did my agent do that?" experiment.
// Creates: Foundry (AIServices) account + project, two model deployments
// (agent model + judge model), Log Analytics + Application Insights,
// the App Insights connection used by Foundry tracing, and RBAC.

@description('Short lowercase prefix, 3-12 chars. Used in all resource names.')
@minLength(3)
@maxLength(12)
param baseName string

param location string = resourceGroup().location

@description('Object ID of the person running the experiment (az ad signed-in-user show --query id -o tsv).')
param userPrincipalId string

// Both deployments use gpt-5-mini: the subscription has no GPT-6 quota (see results/CHANGELOG.md).
// They share one gpt-5-mini quota pool (143K TPM free on 2026-11-16), so keep agent + judge capacity under that.
@description('Model the three agents run on.')
param agentModelName string = 'gpt-5-mini'
param agentModelVersion string = '2025-08-07'
@description('Deployment name for the agent model. Must differ from the judge deployment name.')
param agentDeploymentName string = 'gpt-5-mini-agent'
@description('Thousands of tokens per minute. Lower it if the deployment fails on quota.')
param agentModelCapacity int = 80

@description('Model used as the LLM judge and by the built-in evaluators. Same model as the agents, separate deployment and quota.')
param judgeModelName string = 'gpt-5-mini'
param judgeModelVersion string = '2025-08-07'
@description('Deployment name for the judge model.')
param judgeDeploymentName string = 'gpt-5-mini-judge'
param judgeModelCapacity int = 60

var suffix = uniqueString(resourceGroup().id)
var accountName = toLower('${baseName}-ais-${take(suffix, 5)}')
var projectName = '${baseName}-proj'

// ---------- Monitoring ----------
resource law 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${baseName}-law-${take(suffix, 5)}'
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 90
  }
}

resource appi 'Microsoft.Insights/components@2020-02-02' = {
  name: '${baseName}-appi-${take(suffix, 5)}'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: law.id
    RetentionInDays: 90
  }
}

// ---------- Foundry ----------
resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    allowProjectManagement: true
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: 'Support desk observability experiment'
    description: 'Three-agent support desk (triage, order, policy) for the CIIT 2027 paper.'
  }
}

resource agentDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: agentDeploymentName
  sku: { name: 'GlobalStandard', capacity: agentModelCapacity }
  properties: {
    model: { format: 'OpenAI', name: agentModelName, version: agentModelVersion }
  }
  // Child operations on one account conflict if they run in parallel (RequestConflict), so serialize:
  // project -> agent deployment -> judge deployment -> App Insights connection.
  dependsOn: [ project ]
}

// Deployments on one account must be created one at a time.
resource judgeDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: judgeDeploymentName
  sku: { name: 'GlobalStandard', capacity: judgeModelCapacity }
  properties: {
    model: { format: 'OpenAI', name: judgeModelName, version: judgeModelVersion }
  }
  dependsOn: [ agentDeployment ]
}

// App Insights connection: this is what the portal's Agents > Traces > Connect does.
resource appiConnection 'Microsoft.CognitiveServices/accounts/connections@2025-06-01' = {
  parent: account
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    target: appi.id
    authType: 'ApiKey'
    isSharedToAll: true
    credentials: { key: appi.properties.ConnectionString }
    metadata: { ApiType: 'Azure', ResourceId: appi.id }
  }
  dependsOn: [ judgeDeployment ]
}

// ---------- RBAC ----------
// Azure AI User (renamed Foundry User): build and run agents.
var azureAiUser = '53ca6127-db72-4b80-b1b0-d745d6d5456d'
// Cognitive Services OpenAI User: call the judge deployment with Entra ID.
var openAiUser = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'
// Log Analytics Reader: read traces in the portal.
var logAnalyticsReader = '73c42c96-874c-492b-b04d-ab87d138a893'

resource userAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, userPrincipalId, azureAiUser)
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAiUser)
  }
}

resource userOpenAi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, userPrincipalId, openAiUser)
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUser)
  }
}

resource userLaw 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: law
  name: guid(law.id, userPrincipalId, logAnalyticsReader)
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', logAnalyticsReader)
  }
}

resource userAppi 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: appi
  name: guid(appi.id, userPrincipalId, logAnalyticsReader)
  properties: {
    principalId: userPrincipalId
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', logAnalyticsReader)
  }
}

// Continuous evaluation needs the project's managed identity to hold Azure AI User.
resource projectAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: account
  name: guid(account.id, project.id, azureAiUser)
  properties: {
    principalId: project.identity.principalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', azureAiUser)
  }
}

output projectEndpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'
output openAiEndpoint string = 'https://${accountName}.openai.azure.com/'
output accountName string = accountName
output projectName string = projectName
output agentDeployment string = agentDeployment.name
output judgeDeployment string = judgeDeployment.name
output appInsightsName string = appi.name
