"use strict";var u=Object.defineProperty;var y=Object.getOwnPropertyDescriptor;var v=Object.getOwnPropertyNames;var T=Object.prototype.hasOwnProperty;var w=(a,e)=>{for(var i in e)u(a,i,{get:e[i],enumerable:!0})},P=(a,e,i,l)=>{if(e&&typeof e=="object"||typeof e=="function")for(let c of v(e))!T.call(a,c)&&c!==i&&u(a,c,{get:()=>e[c],enumerable:!(l=y(e,c))||l.enumerable});return a};var k=a=>P(u({},"__esModule",{value:!0}),a);var D={};w(D,{default:()=>S});module.exports=k(D);var o=require("@raycast/api"),d=require("child_process"),p=require("path"),s=require("fs"),m="http://localhost:3049";var $="server.pid",C=`
const http = require("http")
const fs = require("fs")
const path = require("path")

const PORT = 3049
const PID_FILE = path.join(__dirname, "server.pid")

let currentTrackData = null
const pendingCommands = []
const serverStats = {
  startTime: new Date(),
  requestCount: 0,
  lastTrackUpdate: null,
  lastCommandSent: null,
  chromeConnected: false,
  raycastConnected: false,
  pid: process.pid,
}

const AUTH_TOKEN = process.env.LOCAL_API_AUTH_TOKEN;
if (!AUTH_TOKEN) {
    console.error("FATAL: LOCAL_API_AUTH_TOKEN environment variable not set. Server cannot start securely.");
    process.exit(1);
}

try {
  fs.writeFileSync(PID_FILE, process.pid.toString())
} catch (error) {
  console.error('Failed to write PID file:', error);
}

function setCORSHeaders(res) {
  res.setHeader("Access-Control-Allow-Origin", "*")
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization")
}

function parseBody(req) {
  return new Promise((resolve, reject) => {
    let body = ""
    req.on("data", (chunk) => {
      body += chunk.toString()
    })
    req.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {})
      } catch (error) {
        reject(new Error("Invalid JSON body"))
      }
    })
    req.on("error", (err) => {
      reject(err)
    })
  })
}

const server = http.createServer(async (req, res) => {
  serverStats.requestCount++
  const parsedUrl = new URL(req.url, \`http://localhost:\${PORT}\`)
  const pathname = parsedUrl.pathname
  const method = req.method

  setCORSHeaders(res)
  if (method === "OPTIONS") {
    res.writeHead(200)
    res.end()
    return
  }

  if (!(pathname === "/" && method === "GET")) {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        res.writeHead(401, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Unauthorized: Missing or invalid Authorization header" }));
        return;
    }
    const requestToken = authHeader.split(' ')[1];
    if (requestToken !== AUTH_TOKEN) {
        res.writeHead(403, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Forbidden: Invalid token" }));
        return;
    }
  }

  try {
    if (pathname === "/" && method === "GET") {
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end(\`
  <!DOCTYPE html>
  <html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Tidal Raycast API Server</title>
    <style>
      body {
        font-family: system-ui, sans-serif;
        margin: 0;
        background: #f2f2f7;
        color: #1c1c1e;
        line-height: 1.6;
      }
      .container {
        max-width: 700px;
        margin: 4rem auto;
        padding: 2rem;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.05);
      }
      h1 {
        color: #007aff;
        font-size: 1.8rem;
        margin-bottom: 1rem;
      }
      h2 {
        margin-top: 2rem;
        color: #444;
      }
      p {
        margin-bottom: 1rem;
      }
      ul {
        padding-left: 1.2rem;
      }
      li {
        margin-bottom: 0.5rem;
      }
      code {
        background: #f1f1f1;
        padding: 0.2rem 0.4rem;
        border-radius: 4px;
        font-family: monospace;
      }
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Tidal Raycast API Server</h1>
      <p>This server connects your <strong>Raycast</strong> and <strong>Chrome</strong> extensions for a smooth Tidal experience.</p>

      <h2>Endpoints</h2>
      <ul>
        <li><code>POST /track-data</code> \u2014 Send track info from Chrome</li>
        <li><code>GET /current-track</code> \u2014 Get current track in Raycast</li>
        <li><code>POST /send-command</code> \u2014 Send a control command from Raycast</li>
        <li><code>GET /get-command</code> \u2014 Chrome polls for the next command</li>
        <li><code>GET /status</code> \u2014 View server status and metrics</li>
        <li><code>GET /health</code> \u2014 Quick server health check</li>
      </ul>

      <h2>Authentication</h2>
      <p>All API requests (except this page) require a <code>Bearer Token</code> in the <code>Authorization</code> header. Set this in your Raycast preferences.</p>

      <h2>Tips</h2>
      <ul>
        <li>To stop the server, run <strong>"Stop Server"</strong> in Raycast.</li>
        <li>Need help? Run <strong>"Setup Guide"</strong> in Raycast for setup instructions.</li>
      </ul>
    </div>
  </body>
  </html>
\`);
    } else if (pathname === "/track-data" && method === "POST") {
      const trackData = await parseBody(req)
      currentTrackData = { ...trackData, receivedAt: new Date().toISOString() }
      serverStats.lastTrackUpdate = new Date()
      serverStats.chromeConnected = true
      res.writeHead(200, { "Content-Type": "application/json" })
      res.end(JSON.stringify({ status: "success", message: "Track data received" }))
    } else if (pathname === "/get-command" && method === "GET") {
      serverStats.chromeConnected = true
      if (pendingCommands.length > 0) {
        const command = pendingCommands.shift()
        res.writeHead(200, { "Content-Type": "application/json" })
        res.end(JSON.stringify(command))
      } else {
        res.writeHead(200, { "Content-Type": "application/json" })
        res.end(JSON.stringify({ status: "no-commands" }))
      }
    } else if (pathname === "/current-track" && method === "GET") {
      serverStats.raycastConnected = true
      res.writeHead(200, { "Content-Type": "application/json" })
      res.end(JSON.stringify(currentTrackData || { status: "no-data" }))
    } else if (pathname === "/send-command" && method === "POST") {
      const command = await parseBody(req)
      command.timestamp = Date.now()
      command.id = Math.random().toString(36).substr(2, 9)
      pendingCommands.push(command)
      serverStats.lastCommandSent = new Date()
      serverStats.raycastConnected = true
      res.writeHead(200, { "Content-Type": "application/json" })
      res.end(JSON.stringify({ status: "success", message: "Command queued" }))
    } else if (pathname === "/status" && method === "GET") {
      const status = {
        ...serverStats,
        uptime: Date.now() - serverStats.startTime.getTime(),
        currentTrack: currentTrackData,
        pendingCommandsCount: pendingCommands.length,
        port: PORT,
      }
      res.writeHead(200, { "Content-Type": "application/json" })
      res.end(JSON.stringify(status, null, 2))
    } else if (pathname === "/health" && method === "GET") {
      res.writeHead(200, { "Content-Type": "application/json" })
      res.end(JSON.stringify({ status: "healthy", timestamp: new Date().toISOString(), pid: process.pid }))
    } else {
      res.writeHead(404, { "Content-Type": "application/json" })
      res.end(JSON.stringify({ error: "Not found", path: pathname }))
    }
  } catch (error) {
    console.error(\`Request error: \${error.message} for \${method} \${pathname}\`)
    res.writeHead(500, { "Content-Type": "application/json" })
    res.end(JSON.stringify({ error: "Internal server error", message: error.message }))
  }
})

server.on("error", (err) => {
  console.error(\`Server error: \${err.message}\`)
  if (err.code === "EADDRINUSE") {
    console.error(\`Port \${PORT} is already in use. Another server instance might be running.\`)
    process.exit(1)
  }
})

server
  .listen(PORT, () => {
    console.log(\`Server listening on port \${PORT}\`);
  })
  .on("error", (err) => {
    console.error(\`Failed to listen on port \${PORT}: \${err.message}\`)
    process.exit(1)
  })

function gracefulShutdown() {
  server.close(() => {
    try {
      if (fs.existsSync(PID_FILE)) {
        fs.unlinkSync(PID_FILE)
      }
    } catch (error) {
      console.error('Error removing PID file on shutdown:', error);
    }
    process.exit(0)
  })

  setTimeout(() => {
    process.exit(1)
  }, 5000)
}

process.on("SIGINT", gracefulShutdown)
process.on("SIGTERM", gracefulShutdown)

process.on("uncaughtException", (error, origin) => {
  console.error(\`Uncaught exception: \${error.message} at \${origin}]\`)
  console.error(error)
  process.exit(1)
})

process.on("unhandledRejection", (reason, promise) => {
  console.error(\`Unhandled rejection at promise: \${promise}, reason: \${reason}\`)
  console.error(reason)
})

setInterval(() => {
  const now = Date.now()
  if (serverStats.lastTrackUpdate && now - serverStats.lastTrackUpdate.getTime() > 15000) {
    serverStats.chromeConnected = false
  }
}, 5000)
`,r=(a,e="info")=>{console.log(`[TIDAL] [${e.toUpperCase()}] ${a}`)},f=()=>{let{localApiAuthToken:a}=(0,o.getPreferenceValues)();if(!a){let e="Auth token not found in Raycast preferences.";throw r(e,"error"),new Error(e)}return{"Content-Type":"application/json",Authorization:`Bearer ${a}`}};var I=async()=>{try{await(0,o.launchCommand)({name:"stop-server",type:o.LaunchType.Background})}catch(a){await(0,o.showHUD)("\u274C Failed to stop server"),r(`Failed to stop server: ${a}`,"error")}},b=()=>{let a=["/usr/local/bin/node","/opt/homebrew/bin/node","/usr/bin/node","/bin/node",process.execPath];for(let e of a)if((0,s.existsSync)(e))return r(`Found Node.js at: ${e}`),e;try{let e=(0,d.execSync)("which node",{encoding:"utf8"}).trim();if(e&&(0,s.existsSync)(e))return r(`Found Node.js via 'which': ${e}`),e}catch(e){r(`'which node' failed: ${e instanceof Error?e.message:String(e)}`)}return r("Could not find Node.js path, falling back to 'node'"),"node"},g=async()=>{let a=o.environment.supportPath,e=(0,p.join)(a,"server.js"),i=(0,p.join)(a,$);r(`Server dir: ${a}`),r(`Server path: ${e}`),r(`PID file path: ${i}`);let{localApiAuthToken:l}=(0,o.getPreferenceValues)();if(!l)return await(0,o.showHUD)("\u274C Auth Token is not set in preferences!"),r("Auth token is missing from preferences. Cannot start server.","error"),!1;if(!(0,s.existsSync)(e))try{(0,s.writeFileSync)(e,C),r("Created server.js file")}catch(t){return r(`Failed to create server.js: ${t instanceof Error?t.message:String(t)}`),!1}let c=b();if((0,s.existsSync)(i))try{let t=(0,s.readFileSync)(i,"utf8").trim();r(`Found PID file with PID: ${t}`);try{return(0,d.execSync)(`ps -p ${t} -o comm=`),r(`Server process ${t} seems to be running.`),I(),!0}catch(n){r(`Process ${t} not running: ${n instanceof Error?n.message:String(n)}`),(0,s.writeFileSync)(i,"")}}catch(t){r(`Error reading PID file: ${t instanceof Error?t.message:String(t)}`)}try{let t=await fetch(`${m}/health`,{headers:f(),signal:AbortSignal.timeout(500)});if(t.ok){let n=await t.json();return r(`Server already healthy on port 3049 (PID: ${n.pid}).`),await(0,o.showHUD)(`\u2705 Server already running (PID: ${n.pid})`),(!(0,s.existsSync)(i)||(0,s.readFileSync)(i,"utf8").trim()!==String(n.pid))&&((0,s.writeFileSync)(i,String(n.pid)),r(`Updated PID file with PID: ${n.pid}`)),!0}}catch(t){r(`Health check failed: ${t instanceof Error?t.message:String(t)}`,"warn")}r(`Attempting to start server using Node.js at: ${c}`);try{let t=(0,d.spawn)(c,[e],{detached:!0,stdio:"ignore",cwd:a,env:{...process.env,LOCAL_API_AUTH_TOKEN:l,PATH:process.env.PATH||"/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"}});t.unref(),r(`Server process spawned with PID: ${t.pid}`),t.pid&&((0,s.writeFileSync)(i,t.pid.toString()),r(`Wrote new PID ${t.pid} to ${i}`)),await new Promise(n=>setTimeout(n,2500));try{let n=await fetch(`${m}/health`,{headers:f(),signal:AbortSignal.timeout(1e3)});if(n.ok){let h=await n.json();return r(`Server started successfully (PID: ${h.pid}).`),await(0,o.showHUD)(`\u2705 Server started (PID: ${h.pid})`),!0}else throw new Error(`Server responded with ${n.status}`)}catch(n){return r(`Server health check failed after start: ${n instanceof Error?n.message:String(n)}`),await(0,o.showHUD)(`\u274C Server failed to start. Node.js: ${c}`),!1}}catch(t){let n=t instanceof Error?t.message:String(t);return r(`Error spawning server process: ${n}`),await(0,o.showHUD)(`\u274C Failed to start server: ${n}`),!1}};async function S(){await g()}
