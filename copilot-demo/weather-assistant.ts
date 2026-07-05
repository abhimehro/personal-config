import { AzureOpenAI } from "openai";
import { OpenAIRealtimeWS } from "openai/beta/realtime/ws";
import type { OpenAIRealtimeError } from "openai/beta/realtime/internal-base";
import type { RealtimeServerEvent } from "openai/resources/beta/realtime/realtime";
import {
  DefaultAzureCredential,
  getBearerTokenProvider,
} from "@azure/identity";

type RequiredEnvVar = "AZURE_OPENAI_ENDPOINT" | "AZURE_DEPLOYMENT_NAME";

const RESPONSE_INACTIVITY_TIMEOUT_MS = 10000;

function getRequiredEnvVar(name: RequiredEnvVar): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(
      `\n\x1b[31m❌ Missing required environment variable: \x1b[33m${name}\x1b[0m\n\n💡 Please set both \x1b[33mAZURE_OPENAI_ENDPOINT\x1b[0m and \x1b[33mAZURE_DEPLOYMENT_NAME\x1b[0m before running this demo.\n`,
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
  const code = typeof safeError.code === "string" && safeError.code.length > 0
    ? safeError.code
    : "UNKNOWN";

  console.error(`\n\x1b[31m⚠️  Realtime Error (${code}):\x1b[0m ${message}\n`);
}

async function main() {
  const endpoint = normalizeEndpoint(
    getRequiredEnvVar("AZURE_OPENAI_ENDPOINT"),
  );
  const deploymentName = getRequiredEnvVar("AZURE_DEPLOYMENT_NAME");

  // Azure AD authentication
  const credential = new DefaultAzureCredential();
  const tokenProvider = getBearerTokenProvider(
    credential,
    "https://cognitiveservices.azure.com/.default",
  );

  // Create Azure OpenAI client
  const azureClient = new AzureOpenAI({
    azureADTokenProvider: tokenProvider,
    baseURL: endpoint,
    apiVersion: "2024-10-21",
  });

  // Create Realtime WebSocket connection
  const rt = await OpenAIRealtimeWS.azure(azureClient, {
    deploymentName,
  });

  let spinnerInterval: NodeJS.Timeout | null = null;
  const startSpinner = () => {
    if (!process.stdout.isTTY) {
      console.log("Thinking...");
      return;
    }
    const frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
    let i = 0;
    // Hide cursor
    process.stdout.write("\x1B[?25l");
    spinnerInterval = setInterval(() => {
      process.stdout.write(`\r\x1B[K\x1b[36m${frames[i]}\x1b[0m Thinking...`);
      i = (i + 1) % frames.length;
    }, 80);
  };

  const stopSpinner = () => {
    if (spinnerInterval) {
      clearInterval(spinnerInterval);
      spinnerInterval = null;
      // Clear line and restore cursor conditionally
      if (process.stdout.isTTY) {
        process.stdout.write("\r\x1B[K\x1B[?25h");
      }
    }
  };

  // Handle graceful exit
  process.on("SIGINT", () => {
    stopSpinner();
    if (process.stdout.isTTY) {
      process.stdout.write("\r\x1B[K\x1B[?25h");
    }
    console.log("\n👋 Cancelled by user. Goodbye!");
    process.exit(130);
  });

  let resolveResponseDone: () => void = () => {};
  const responseDone = new Promise<void>((resolve) => {
    resolveResponseDone = resolve;
  });
  let responseInactivityTimeout: NodeJS.Timeout | undefined;
  const resetResponseInactivityTimeout = () => {
    if (responseInactivityTimeout) {
      clearTimeout(responseInactivityTimeout);
    }
    responseInactivityTimeout = setTimeout(
      resolveResponseDone,
      RESPONSE_INACTIVITY_TIMEOUT_MS,
    );
  };

  // Set up event handlers
  rt.on("error", (error: OpenAIRealtimeError) => {
    stopSpinner();
    handleRealtimeError(error);
    resolveResponseDone();
  });
  rt.on("session.created", () => console.log("Session created\n"));

  let isFirstDelta = true;
  // Handle response text streaming
  rt.on(
    "response.text.delta",
    (event: Extract<RealtimeServerEvent, { type: "response.text.delta" }>) => {
      if (isFirstDelta) {
        stopSpinner();
        const prefix = process.stdout.isTTY
          ? "\x1b[32mAssistant:\x1b[0m "
          : "Assistant: ";
        process.stdout.write(prefix);
        isFirstDelta = false;
      }
      process.stdout.write(event.delta);
      resetResponseInactivityTimeout();
    },
  );

  // Handle response completion
  rt.on("response.done", () => {
    console.log("\n");
    resolveResponseDone();
  });

  const question = "What's the weather like in Seattle?";
  const youPrefix = process.stdout.isTTY ? "\x1b[36mYou:\x1b[0m " : "You: ";
  console.log(`${youPrefix}${question}`);

  // Send text message
  rt.send({
    type: "conversation.item.create",
    item: {
      type: "message",
      role: "user",
      content: [{ type: "input_text", text: question }],
    },
  });

  // Trigger response generation
  rt.send({ type: "response.create" });
  startSpinner();

  // Keep connection open for response
  resetResponseInactivityTimeout();
  await responseDone;
  if (responseInactivityTimeout) {
    clearTimeout(responseInactivityTimeout);
  }

  stopSpinner();
  await rt.close();
}

main().catch((error: unknown) => {
  const message = error instanceof Error
    ? error.message
    : "Unknown startup failure";
  console.error(`\n\x1b[31m❌ Startup failed:\x1b[0m ${message}`);
  process.exitCode = 1;
});
