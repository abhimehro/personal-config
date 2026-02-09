import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";
import * as readline from "readline";

const COLORS = {
  Reset: "\x1b[0m",
  Cyan: "\x1b[36m",
  Green: "\x1b[32m",
  Dim: "\x1b[2m",
};

class Spinner {
  private timer: NodeJS.Timeout | null = null;
  private frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];
  private currentFrame = 0;

  start(text: string = "Thinking...") {
    if (this.timer) return;
    process.stdout.write("\x1B[?25l"); // Hide cursor
    this.timer = setInterval(() => {
      process.stdout.write(`\r${COLORS.Cyan}${this.frames[this.currentFrame]} ${text}${COLORS.Reset}`);
      this.currentFrame = (this.currentFrame + 1) % this.frames.length;
    }, 80);
  }

  stop() {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
      process.stdout.write("\r\x1B[K"); // Clear line
      process.stdout.write("\x1B[?25h"); // Show cursor
    }
  }

  isSpinning() {
    return this.timer !== null;
  }
}

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

const spinner = new Spinner();

session.on((event: SessionEvent) => {
  if (event.type === "assistant.message_delta") {
    if (spinner.isSpinning()) {
      spinner.stop();
      process.stdout.write(`${COLORS.Green}Assistant:${COLORS.Reset} `);
    }
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

    try {
      spinner.start();
      await session.sendAndWait({ prompt: input });
    } catch (error) {
      // Error handling is managed by the session mostly, but good to catch unexpected errors
      spinner.stop();
      const errorMessage =
        error instanceof Error ? error.stack ?? error.message : String(error);
      console.error(`\n${COLORS.Dim}Error: ${errorMessage}${COLORS.Reset}`);
    } finally {
      spinner.stop();
    }

    console.log("\n");
    prompt();
  });
};

prompt();
