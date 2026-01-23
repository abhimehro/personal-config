import { CopilotClient, defineTool, SessionEvent } from "@github/copilot-sdk";
import * as readline from "readline";

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
    process.stdout.write(event.data.deltaContent);
  }
});

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

console.log("🌤️  Weather Assistant (type 'exit' to quit)");
console.log("   Try: 'What's the weather in Paris?'\n");

const prompt = () => {
  rl.question("You: ", async (input) => {
    if (input.toLowerCase() === "exit") {
      await client.stop();
      rl.close();
      process.exit(0);
    }

    process.stdout.write("Assistant: ");
    await session.sendAndWait({ prompt: input });
    console.log("\n");
    prompt();
  });
};

prompt();
