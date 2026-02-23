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

const thinkingMessages = [
  "Consulting the clouds...",
  "Checking satellite data...",
  "Asking the wind...",
  "Reading the barometer...",
  "Forecasting...",
  "Looking at the sky...",
];

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
  const msg = thinkingMessages[Math.floor(Math.random() * thinkingMessages.length)];
  process.stdout.write(ANSI.HideCursor);
  spinnerInterval = setInterval(() => {
    process.stdout.write(
      `\r${COLORS.Green}Assistant:${COLORS.Reset} ${spinnerFrames[i]} ${COLORS.Dim}(${msg})${COLORS.Reset}`,
    );
    i = (i + 1) % spinnerFrames.length;
  }, 80);
};

// Ensure cursor is restored on exit
process.on("exit", () => {
  process.stdout.write(ANSI.ShowCursor);
});

// Helper functions for emojis
const getWeatherEmoji = (condition: string): string => {
  const normalized = condition.toLowerCase();
  if (normalized.includes("sunny") || normalized.includes("clear")) return "☀️";
  if (normalized.includes("partly cloudy")) return "⛅";
  if (normalized.includes("cloudy") || normalized.includes("overcast"))
    return "☁️";
  if (
    normalized.includes("rain") ||
    normalized.includes("drizzle") ||
    normalized.includes("shower")
  )
    return "🌧️";
  if (normalized.includes("thunder")) return "⛈️";
  if (normalized.includes("snow") || normalized.includes("blizzard"))
    return "❄️";
  if (normalized.includes("fog") || normalized.includes("mist")) return "🌫️";
  return "🌡️";
};

const getTimeEmoji = (date: Date): string => {
  const hour = date.getHours();
  // Map 0-11 and 12-23 to 0-11 index
  const clockIndex = hour % 12;
  const clocks = [
    "🕛",
    "🕐",
    "🕑",
    "🕒",
    "🕓",
    "🕔",
    "🕕",
    "🕖",
    "🕗",
    "🕘",
    "🕙",
    "🕚",
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
        temperature: `${current.temp_F}°F (${current.temp_C}°C)`,
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

const getGreeting = () => {
  const hour = new Date().getHours();
  if (hour < 5) return "Burning the midnight oil? 🦉";
  if (hour < 12) return "Good morning! 🌅";
  if (hour < 18) return "Good afternoon! ☀️";
  return "Good evening! 🌙";
};

console.log(`${COLORS.Cyan}
╔══════════════════════════════════════════════╗
║           🌤️  Weather Assistant CLI          ║
╚══════════════════════════════════════════════╝${COLORS.Reset}`);
console.log(
  `${COLORS.Dim}   ${getGreeting()} Try: 'What's the weather in Paris?'${COLORS.Reset}\n`,
);

// Graceful shutdown on Ctrl+C
rl.on('SIGINT', async () => {
  stopSpinner();
  console.log(`\n${COLORS.Green}Goodbye! 👋${COLORS.Reset}`);
  try {
    await client.stop();
  } catch (e) {
    // Ignore error on stop if not started properly or already stopped
  }
  rl.close();
  process.exit(0);
});

const prompt = () => {
  rl.question(`${COLORS.Cyan}You:${COLORS.Reset} `, async (input) => {
    if (input.trim() === "") {
      console.log(`${COLORS.Dim}Tip: Try asking "What's the weather in Tokyo?"${COLORS.Reset}`);
      prompt();
      return;
    }

    if (input.trim().toLowerCase() === "clear") {
      console.clear();
      prompt();
      return;
    }

    if (input.toLowerCase() === "exit") {
      console.log(`${COLORS.Green}Goodbye! 👋${COLORS.Reset}`);
      await client.stop();
      rl.close();
      process.exit(0);
    }

    if (input.trim().toLowerCase() === "help") {
      console.log(`
${COLORS.Cyan}🤖 Capabilities:${COLORS.Reset}
  • 🌤️  Get current weather for any city
  • 🕒 Get current local time

${COLORS.Cyan}💡 Examples:${COLORS.Reset}
  • "What's the weather in Tokyo?"
  • "Is it raining in London?"
  • "What time is it?"

${COLORS.Cyan}Commands:${COLORS.Reset}
  • clear - Clear the screen
  • help - Show this message
  • exit - Quit the application
`);
      prompt();
      return;
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
