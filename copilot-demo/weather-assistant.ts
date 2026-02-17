import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";
import * as readline from "readline";

const COLORS = {
  Reset: "\x1b[0m",
  Cyan: "\x1b[36m",
  Green: "\x1b[32m",
  Dim: "\x1b[2m",
};

const ANSI = {
  HideCursor: "\x1B[?25l",
  ShowCursor: "\x1B[?25h",
  ClearLine: "\x1B[K",
};

const spinnerFrames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
let spinnerInterval: NodeJS.Timeout | undefined;

const stopSpinner = () => {
  if (spinnerInterval) {
    clearInterval(spinnerInterval);
    spinnerInterval = undefined;
    process.stdout.write(ANSI.ShowCursor);
    process.stdout.write(`\r${COLORS.Green}Assistant:${COLORS.Reset} `);
    process.stdout.write(ANSI.ClearLine);
  }
};

const startSpinner = () => {
  if (spinnerInterval) return; // Prevent multiple spinners
  let i = 0;
  process.stdout.write(ANSI.HideCursor);
  spinnerInterval = setInterval(() => {
    process.stdout.write(
      `\r${COLORS.Green}Assistant:${COLORS.Reset} ${spinnerFrames[i]} `,
    );
    i = (i + 1) % spinnerFrames.length;
  }, 80);
};

// Ensure cursor is restored on exit
process.on("exit", () => {
  process.stdout.write(ANSI.ShowCursor);
});

// Ensure cursor is restored on exit or interrupt
process.on("SIGINT", () => {
  stopSpinner();
  process.stdout.write("\n");
  process.exitCode = 130; // Use standard interrupt exit code so callers can detect cancellation
});

// Safety net: restore cursor on any exit (e.g., uncaught exceptions)
// Note: spinnerInterval will be undefined if stopSpinner() was already called,
// so this only acts when the process exits abnormally without cleanup
process.on("exit", () => {
  if (spinnerInterval) {
    clearInterval(spinnerInterval);
    process.stdout.write("\x1B[?25h"); // Show cursor
  }
});

const getWeather = defineTool("get_weather", {
  description: "Get the current weather for a city",
  parameters: {
    type: "object",
    properties: {
      city: { type: "string", description: "The city name" },
    },
    required: ["city"],
  },
  handler: async (args: { city: string }) => {
    const { city } = args;
    try {
      const response = await fetch(
        `https://wttr.in/${encodeURIComponent(city)}?format=j1`,
      );
      const data = await response.json();
      const current = data.current_condition[0];
      return {
        city,
        temperature: `${current.temp_F}°F (${current.temp_C}°C)`,
        condition: current.weatherDesc[0].value,
        humidity: `${current.humidity}%`,
        wind: `${current.windspeedMiles}mph`,
      };
    } catch (error) {
      return { error: "Failed to fetch weather data" };
    }
  },
});

const getCurrentTime = defineTool("get_current_time", {
  description: "Get the current local system time",
  parameters: { type: "object", properties: {} },
  handler: async () => {
    return { time: new Date().toLocaleString() };
  },
});

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  streaming: true,
  tools: [getWeather, getCurrentTime],
});

session.on((event: SessionEvent) => {
  if (event.type === "assistant.message_delta") {
    stopSpinner();
    process.stdout.write(event.data.deltaContent);
  }
});

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

console.log("🌤️  Weather Assistant (type 'exit' to quit)");
console.log(
  `${COLORS.Dim}   Try: 'What's the weather in Paris?'${COLORS.Reset}\n`,
);

const prompt = () => {
  rl.question(`${COLORS.Cyan}You:${COLORS.Reset} `, async (input) => {
    if (input.trim() === "") {
      prompt();
      return;
    }

    if (input.toLowerCase() === "exit") {
      console.log(`${COLORS.Green}Goodbye! 👋${COLORS.Reset}`);
      await client.stop();
      rl.close();
      process.exit(0);
    }

    startSpinner();
    try {
      await session.sendAndWait({ prompt: input });
    } finally {
      stopSpinner();
    }
    console.log("\n");
    prompt();
  });
};

prompt();
