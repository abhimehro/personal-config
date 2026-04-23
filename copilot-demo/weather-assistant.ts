import { AzureOpenAI } from "openai";
import { OpenAIRealtimeWS } from "openai/beta/realtime/ws";
import type { OpenAIRealtimeError } from "openai/beta/realtime/internal-base";
import type { RealtimeServerEvent } from "openai/resources/beta/realtime/realtime";
import { DefaultAzureCredential, getBearerTokenProvider } from "@azure/identity";

type RequiredEnvVar = "AZURE_OPENAI_ENDPOINT" | "AZURE_DEPLOYMENT_NAME";

function getRequiredEnvVar(name: RequiredEnvVar): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${name}. Set AZURE_OPENAI_ENDPOINT and AZURE_DEPLOYMENT_NAME before running this demo.`,
    );
  }

  return value;
}

function normalizeEndpoint(rawEndpoint: string): string {
  const endpoint = rawEndpoint.trim().replace(/\/+$/, "");
  if (!endpoint.startsWith("https://")) {
    throw new Error("AZURE_OPENAI_ENDPOINT must start with https://");
  }

  return `${endpoint}/openai`;
}

function handleRealtimeError(error: OpenAIRealtimeError): void {
  const safeError = error as { message?: unknown; code?: unknown };
  const message =
    typeof safeError.message === "string" && safeError.message.length > 0
      ? safeError.message
      : "Unknown realtime error";
  const code =
    typeof safeError.code === "string" && safeError.code.length > 0
      ? safeError.code
      : "UNKNOWN";

  console.error(`[realtime:error] code=${code} message=${message}`);
}

async function main ()
{
  const endpoint = normalizeEndpoint(getRequiredEnvVar("AZURE_OPENAI_ENDPOINT"));
  const deploymentName = getRequiredEnvVar("AZURE_DEPLOYMENT_NAME");

  // Azure AD authentication
  const credential = new DefaultAzureCredential();
  const tokenProvider = getBearerTokenProvider(
    credential,
    "https://cognitiveservices.azure.com/.default"
  );

  // Create Azure OpenAI client
  const azureClient = new AzureOpenAI( {
    azureADTokenProvider: tokenProvider,
    baseURL: endpoint,
    apiVersion: "2024-10-21",
  } );

  // Create Realtime WebSocket connection
  const rt = await OpenAIRealtimeWS.azure( azureClient, {
    deploymentName,
  } );

  // Set up event handlers
  rt.on( "error", ( error: OpenAIRealtimeError ) => handleRealtimeError(error) );
  rt.on( "session.created", () => console.log( "Session created" ) );

  // Handle response text streaming
  rt.on( "response.text.delta", ( event: Extract<RealtimeServerEvent, { type: "response.text.delta" }> ) =>
  {
    process.stdout.write( event.delta );
  } );

  // Handle response completion
  rt.on( "response.done", () =>
  {
    console.log( "\n[Response complete]" );
  } );

  // Send text message
  rt.send( {
    type: "conversation.item.create",
    item: {
      type: "message",
      role: "user",
      content: [ { type: "input_text", text: "What's the weather like in Seattle?" } ],
    },
  } );

  // Trigger response generation
  rt.send( { type: "response.create" } );

  // Keep connection open for response
  await new Promise( ( resolve ) => setTimeout( resolve, 10000 ) );

  await rt.close();
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : "Unknown startup failure";
  console.error(`[startup:error] ${message}`);
  process.exitCode = 1;
});
