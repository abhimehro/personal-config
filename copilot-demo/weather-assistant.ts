import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";
import * as readline from "readline";

const isTTY = !!process.stdout.isTTY;

const COLORS = {
  Reset: isTTY ? "\x1b[0m" : "",
  Cyan: isTTY ? "\x1b[36m" : "",
  Green: isTTY ? "\x1b[32m" : "",
  Red: isTTY ? "\x1b[31m" : "",
  Dim: isTTY ? "\x1b[2m" : "",
};

const ANSI = {
  HideCursor: isTTY ? "\x1B[?25l" : "",
  ShowCursor: isTTY ? "\x1B[?25h" : "",
  ClearLine: isTTY ? "\x1B[K" : "",
};

const spinnerFrames = ["\u280b", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2827", "\u2807", "\u280f"];
let spinnerInterval: NodeJS.Timeout | undefined;

const thinkingMessages = [
  "Consulting the clouds...",
  "Checking satellite data...",
  "Asking the wind...",
  "Reading the barometer...",
  "Forecasting...",
  "Looking at the sky...",
];

const clearSpinner = () => {
  if (spinnerInterval) {
    clearInterval(spinnerInterval);
    spinnerInterval = undefined;
    if (process.stdout.isTTY) {
      process.stdout.write("\r" + ANSI.ClearLine + ANSI.ShowCursor);
    }
  }
};

const startSpinner = () => {
  if (spinnerInterval) return; // Prevent multiple spinners
  let i = 0;
  const msg =
    thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];

  // Fallback for non-TTY (CI, screen readers) or when terminal isn't fully interactive
  if (!process.stdout.isTTY) {
    process.stdout.write(
      `${COLORS.Dim}(${msg})${COLORS.Reset}\n`,
    );
    return;
  }

  process.stdout.write(ANSI.HideCursor);
  spinnerInterval = setInterval(() => {
    process.stdout.write(
      `\r${spinnerFrames[i]} ${COLORS.Dim}(${msg})${COLORS.Reset}`,
    );
    i = (i + 1) % spinnerFrames.length;
  }, 80);
};

// Ensure cursor is restored on exit
process.on("exit", () => {
  if (process.stdout.isTTY) {
    process.stdout.write(ANSI.ShowCursor);
  }
});

// Helper functions for emojis
const getWeatherEmoji = (condition: string): string => {
  const normalized = condition.toLowerCase();
  if (normalized.includes("sunny") || normalized.includes("clear")) return "\u2600\ufe0f";
  if (normalized.includes("partly cloudy")) return "\u26c5";
  if (normalized.includes("cloudy") || normalized.includes("overcast"))
    return "\u2601\ufe0f";
  if (
    normalized.includes("rain") ||
    normalized.includes("drizzle") ||
    normalized.includes("shower")
  )
    return "\ud83c\udf27\ufe0f";
  if (normalized.includes("thunder")) return "\u26c8\ufe0f";
  if (normalized.includes("snow") || normalized.includes("blizzard"))
    return "\u2744\ufe0f";
  if (normalized.includes("fog") || normalized.includes("mist")) return "\ud83c\udf2b\ufe0f";
  return "\ud83c\udf21\ufe0f";
};

const getTimeEmoji = (date: Date): string => {
  const hour = date.getHours();
  // Map 0-11 and 12-23 to 0-11 index
  const clockIndex = hour % 12;
  const clocks = [
    "\ud83d\udd5b",
    "\ud83d\udd50",
    "\ud83d\udd51",
    "\ud83d\udd52",
    "\ud83d\udd53",
    "\ud83d\udd54",
    "\ud83d\udd55",
    "\ud83d\udd56",
    "\ud83d\udd57",
    "\ud83d\udd58",
    "\ud83d\udd59",
    "\ud83d\udd5a",
  ];
  return clocks[clockIndex];
};

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
      if (!response.ok) {
        return { error: `Weather data not found for ${city}` };
      }
      const data = await response.json();
      const current = data.current_condition[0];
      const condition = current.weatherDesc[0].value;
      return {
        city,
        temperature: `${current.temp_F}\u00b0F (${current.temp_C}\u00b0C)`,
        condition: `${condition} ${getWeatherEmoji(condition)}`,
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
    const now = new Date();
    return { time: `${getTimeEmoji(now)} ${now.toLocaleString()}` };
  },
});

const client = new CopilotClient();
const session = await client.createSession({
  model: "gpt-4.1",
  streaming: true,
  tools: [getWeather, getCurrentTime],
});

let responseStarted = false;

session.on((event: SessionEvent) => {
  if (event.type === "assistant.message_delta") {
    if (!responseStarted) {
      clearSpinner();
      process.stdout.write(
        COLORS.Green + "Assistant:" + COLORS.Reset + " "
      );
      responseStarted = true;
    }
    process.stdout.write(event.data.deltaContent);
  }
});

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

const TIPS = [
  'Try asking "What\'s the weather in Tokyo?"',
  'Try asking "What time is it right now?"',
  'Try asking "Is it raining in London?"',
  "You can type 'help' to see available commands.",
  "Type 'clear' to reset the screen.",
];

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 5) return "Burning the midnight oil? \ud83e\udd89";
  if (hour < 12) return "Good morning! \ud83c\udf05";
  if (hour < 18) return "Good afternoon! \u2600\ufe0f";
  return "Good evening! \ud83c\udf19";
};

const printHeader = () => {
  console.log(`${COLORS.Cyan}
\u256c\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2563
\u2551           \ud83c\udf24\ufe0f  Weather Assistant CLI          \u2551
\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d${COLORS.Reset}`);
  console.log(
    `${COLORS.Dim}   ${getGreeting()} Try: 'What's the weather in Paris?'
   Type 'help' to see available commands, or 'exit' to quit.${COLORS.Reset}\n`,
  );
};

printHeader();

const handleShutdown = async () => {
  clearSpinner();
  if (process.stdout.isTTY) {
    process.stdout.write("\r" + ANSI.ClearLine);
  }
  console.log(`${COLORS.Green}Goodbye! \ud83d\udc4b${COLORS.Reset}`);
  try {
    await client.stop();
  } catch (e) {
    // Ignore error on stop if not started properly or already stopped
  }
  rl.close();
  process.exit(0);
};

// Graceful shutdown on Ctrl+C
rl.on("SIGINT", handleShutdown);

// Graceful shutdown on EOF (Ctrl+D)
rl.on("close", handleShutdown);

const prompt = () => {
  rl.question(`${COLORS.Cyan}You:${COLORS.Reset} `, async (input) => {
    if (input.trim() === "") {
      const tip = TIPS[Math.floor(Math.random() * TIPS.length)];
      console.log(`${COLORS.Dim}Tip: ${tip}${COLORS.Reset}`);
      prompt();
      return;
    }

    if (["clear", "cls"].includes(input.trim().toLowerCase())) {
      console.clear();
      printHeader();
      prompt();
      return;
    }

    if (["exit", "quit", "q"].includes(input.trim().toLowerCase())) {
      console.log(`${COLORS.Green}Goodbye! \ud83d\udc4b${COLORS.Reset}`);
      await client.stop();
      rl.close();
      process.exit(0);
    }

    if (input.trim().toLowerCase() === "help") {
      console.log(`
${COLORS.Cyan}\ud83e\udd16 Capabilities:${COLORS.Reset}
  \u2022 \ud83c\udf24\ufe0f  Get current weather for any city
  \u2022 \ud83d\udd52 Get current local time

${COLORS.Cyan}\ud83d\udca1 Examples:${COLORS.Reset}
  \u2022 "What's the weather in Tokyo?"
  \u2022 "Is it raining in London?"
  \u2022 "What time is it?"

${COLORS.Cyan}Commands:${COLORS.Reset}
  \u2022 clear (or cls)    - Clear the screen
  \u2022 help              - Show this message
  \u2022 exit (or quit, q) - Quit the application
`);
      prompt();
      return;
    }

    startSpinner();
    responseStarted = false;
    try {
      await session.sendAndWait({ prompt: input });
    } catch (err: any) {
      clearSpinner();
      console.log(
        `${COLORS.Red}Error:${COLORS.Reset} Could not reach the assistant. Please try again. (${err?.message || "Unknown error"})`
      );
    } finally {
      clearSpinner();
    }
    console.log("\n");
    prompt();
  });
};

prompt();
