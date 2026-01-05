"use strict";"use client";var v=Object.defineProperty;var b=Object.getOwnPropertyDescriptor;var A=Object.getOwnPropertyNames;var D=Object.prototype.hasOwnProperty;var E=(t,n)=>{for(var s in n)v(t,s,{get:n[s],enumerable:!0})},R=(t,n,s,c)=>{if(n&&typeof n=="object"||typeof n=="function")for(let p of A(n))!D.call(t,p)&&p!==s&&v(t,p,{get:()=>n[p],enumerable:!(c=b(n,p))||c.enumerable});return t};var x=t=>R(v({},"__esModule",{value:!0}),t);var L={};E(L,{default:()=>$});module.exports=x(L);var r=require("@raycast/api"),h=require("react");var i=require("@raycast/api"),g=require("child_process"),f=require("path"),l=require("fs"),S="http://localhost:3049",O=1e3,T="server.pid",F=`
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
`,o=(t,n="info")=>{console.log(`[TIDAL] [${n.toUpperCase()}] ${t}`)},y=()=>{let{localApiAuthToken:t}=(0,i.getPreferenceValues)();if(!t){let n="Auth token not found in Raycast preferences.";throw o(n,"error"),new Error(n)}return{"Content-Type":"application/json",Authorization:`Bearer ${t}`}};var w=async()=>{try{let t=await fetch(`${S}/status`,{headers:y(),signal:AbortSignal.timeout(O)});return t.ok?await t.json():null}catch(t){return o(`Failed to get server status: ${t}`,"error"),null}};var N=async()=>{try{await(0,i.launchCommand)({name:"stop-server",type:i.LaunchType.Background})}catch(t){await(0,i.showHUD)("\u274C Failed to stop server"),o(`Failed to stop server: ${t}`,"error")}},H=()=>{let t=["/usr/local/bin/node","/opt/homebrew/bin/node","/usr/bin/node","/bin/node",process.execPath];for(let n of t)if((0,l.existsSync)(n))return o(`Found Node.js at: ${n}`),n;try{let n=(0,g.execSync)("which node",{encoding:"utf8"}).trim();if(n&&(0,l.existsSync)(n))return o(`Found Node.js via 'which': ${n}`),n}catch(n){o(`'which node' failed: ${n instanceof Error?n.message:String(n)}`)}return o("Could not find Node.js path, falling back to 'node'"),"node"},C=async()=>{let t=i.environment.supportPath,n=(0,f.join)(t,"server.js"),s=(0,f.join)(t,T);o(`Server dir: ${t}`),o(`Server path: ${n}`),o(`PID file path: ${s}`);let{localApiAuthToken:c}=(0,i.getPreferenceValues)();if(!c)return await(0,i.showHUD)("\u274C Auth Token is not set in preferences!"),o("Auth token is missing from preferences. Cannot start server.","error"),!1;if(!(0,l.existsSync)(n))try{(0,l.writeFileSync)(n,F),o("Created server.js file")}catch(a){return o(`Failed to create server.js: ${a instanceof Error?a.message:String(a)}`),!1}let p=H();if((0,l.existsSync)(s))try{let a=(0,l.readFileSync)(s,"utf8").trim();o(`Found PID file with PID: ${a}`);try{return(0,g.execSync)(`ps -p ${a} -o comm=`),o(`Server process ${a} seems to be running.`),N(),!0}catch(e){o(`Process ${a} not running: ${e instanceof Error?e.message:String(e)}`),(0,l.writeFileSync)(s,"")}}catch(a){o(`Error reading PID file: ${a instanceof Error?a.message:String(a)}`)}try{let a=await fetch(`${S}/health`,{headers:y(),signal:AbortSignal.timeout(500)});if(a.ok){let e=await a.json();return o(`Server already healthy on port 3049 (PID: ${e.pid}).`),await(0,i.showHUD)(`\u2705 Server already running (PID: ${e.pid})`),(!(0,l.existsSync)(s)||(0,l.readFileSync)(s,"utf8").trim()!==String(e.pid))&&((0,l.writeFileSync)(s,String(e.pid)),o(`Updated PID file with PID: ${e.pid}`)),!0}}catch(a){o(`Health check failed: ${a instanceof Error?a.message:String(a)}`,"warn")}o(`Attempting to start server using Node.js at: ${p}`);try{let a=(0,g.spawn)(p,[n],{detached:!0,stdio:"ignore",cwd:t,env:{...process.env,LOCAL_API_AUTH_TOKEN:c,PATH:process.env.PATH||"/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"}});a.unref(),o(`Server process spawned with PID: ${a.pid}`),a.pid&&((0,l.writeFileSync)(s,a.pid.toString()),o(`Wrote new PID ${a.pid} to ${s}`)),await new Promise(e=>setTimeout(e,2500));try{let e=await fetch(`${S}/health`,{headers:y(),signal:AbortSignal.timeout(1e3)});if(e.ok){let u=await e.json();return o(`Server started successfully (PID: ${u.pid}).`),await(0,i.showHUD)(`\u2705 Server started (PID: ${u.pid})`),!0}else throw new Error(`Server responded with ${e.status}`)}catch(e){return o(`Server health check failed after start: ${e instanceof Error?e.message:String(e)}`),await(0,i.showHUD)(`\u274C Server failed to start. Node.js: ${p}`),!1}}catch(a){let e=a instanceof Error?a.message:String(a);return o(`Error spawning server process: ${e}`),await(0,i.showHUD)(`\u274C Failed to start server: ${e}`),!1}},P=async()=>{let t=i.environment.supportPath,n=(0,f.join)(t,T);o(`Attempting to stop server. PID file path: ${n}`);let s=null,c=null,p=async()=>{try{let e=await fetch(`${S}/health`,{headers:y(),signal:AbortSignal.timeout(500)});if(e.ok){let u=await e.json();if(u&&typeof u.pid=="number")return u.pid}}catch(e){o(`Health check failed: ${e instanceof Error?e.message:String(e)}`,"warn")}return null};if((0,l.existsSync)(n))try{c=(0,l.readFileSync)(n,"utf8").trim(),c?(s=parseInt(c),o(`Found PID file with PID: ${s}`)):o("PID file is empty.")}catch(e){o(`Error reading PID file: ${e instanceof Error?e.message:String(e)}.`,"warn")}else o("PID file not found.");if(s===null)if(o("No PID from file. Checking server health endpoint for active PID."),s=await p(),s)o(`Found active server PID from health endpoint: ${s}`);else return o("Server not detected as running via health endpoint. Nothing to stop.","warn"),await(0,i.showHUD)("\u26A0\uFE0F Server not running"),!1;try{o(`Attempting to send SIGTERM to PID: ${s}`),process.kill(s,"SIGTERM"),o(`Sent SIGTERM to PID: ${s}`),await new Promise(e=>setTimeout(e,1e3))}catch(e){o(`Error sending SIGTERM to PID ${s}: ${e instanceof Error?e.message:String(e)}. Process might not exist or already stopped.`,"warn")}let a=await p();if(a===null){if(o("Server stopped successfully (final health check failed)."),await(0,i.showHUD)("\u2705 Server stopped"),(0,l.existsSync)(n))try{(0,l.unlinkSync)(n),o("PID file removed.")}catch(u){o(`Error removing PID file: ${u instanceof Error?u.message:String(u)}`,"error")}let e=(0,f.join)(t,"server.js");if((0,l.existsSync)(e))try{(0,l.unlinkSync)(e),o("server.js file removed.")}catch(u){o(`Error removing server.js file: ${u instanceof Error?u.message:String(u)}`,"error")}return!0}else{let e=`\u274C Server still running (PID: ${a}).`;return c&&a===parseInt(c)?e+=` Original PID ${c} is still active.`:c&&a!==parseInt(c)?e+=` New PID ${a} detected, original PID ${c} might have been replaced.`:e+=" No original PID file found.",o(e,"error"),await(0,i.showHUD)(e),!1}},k=t=>{let n=Math.floor(t/1e3),s=Math.floor(n/60),c=Math.floor(s/60);return c>0?`${c}h ${s%60}m`:s>0?`${s}m ${n%60}s`:`${n}s`};var d=require("react/jsx-runtime");function $(){let[t,n]=(0,h.useState)(null),[s,c]=(0,h.useState)(!0),[p,a]=(0,h.useState)(null),e=async()=>{try{let m=await w();m?(n(m),a(null)):(a("Server not reachable"),n(null))}catch(m){console.error("Error fetching server status:",m),a("Server not reachable"),n(null)}finally{c(!1)}},u=async()=>{c(!0),await C(),setTimeout(e,2e3)},I=async()=>{c(!0),await P(),setTimeout(e,1e3)};return(0,h.useEffect)(()=>{e();let m=setInterval(e,2e3);return()=>clearInterval(m)},[]),s?(0,d.jsx)(r.List,{isLoading:!0}):p?(0,d.jsx)(r.List,{children:(0,d.jsx)(r.List.Item,{title:"Server Status",subtitle:p,icon:{source:r.Icon.XMarkCircle,tintColor:r.Color.Red},actions:(0,d.jsxs)(r.ActionPanel,{children:[(0,d.jsx)(r.Action,{title:"Start Server",onAction:u,icon:r.Icon.Play}),(0,d.jsx)(r.Action,{title:"Refresh",onAction:e,icon:r.Icon.RotateClockwise})]})})}):(0,d.jsxs)(r.List,{children:[(0,d.jsxs)(r.List.Section,{title:"Server Status",children:[(0,d.jsx)(r.List.Item,{title:"Server",subtitle:`Running on port ${t?.port}`,icon:{source:r.Icon.CheckCircle,tintColor:r.Color.Green},accessories:[{text:`Uptime: ${k(t?.uptime||0)}`}],actions:(0,d.jsxs)(r.ActionPanel,{children:[(0,d.jsx)(r.Action,{title:"Stop Server",onAction:I,icon:r.Icon.Stop}),(0,d.jsx)(r.Action,{title:"Refresh",onAction:e,icon:r.Icon.RotateClockwise})]})}),(0,d.jsx)(r.List.Item,{title:"Requests",subtitle:`${t?.requestCount} total requests`,icon:{source:r.Icon.BarChart,tintColor:r.Color.Blue}})]}),(0,d.jsxs)(r.List.Section,{title:"Connections",children:[(0,d.jsx)(r.List.Item,{title:"Chrome Extension",subtitle:t?.chromeConnected?"Connected":"Disconnected",icon:{source:t?.chromeConnected?r.Icon.CheckCircle:r.Icon.XMarkCircle,tintColor:t?.chromeConnected?r.Color.Green:r.Color.Red},accessories:t?.lastTrackUpdate?[{text:`Last update: ${new Date(t.lastTrackUpdate).toLocaleTimeString()}`}]:[{text:"No updates"}]}),(0,d.jsx)(r.List.Item,{title:"Raycast Extension",subtitle:t?.raycastConnected?"Connected":"Disconnected",icon:{source:t?.raycastConnected?r.Icon.CheckCircle:r.Icon.XMarkCircle,tintColor:t?.raycastConnected?r.Color.Green:r.Color.Red},accessories:t?.lastCommandSent?[{text:`Last command: ${new Date(t.lastCommandSent).toLocaleTimeString()}`}]:[{text:"No commands"}]})]}),(0,d.jsxs)(r.List.Section,{title:"Current State",children:[(0,d.jsx)(r.List.Item,{title:"Track",subtitle:t?.currentTrack?.title?`${t.currentTrack.title} - ${t.currentTrack.artist}`:"No track data",icon:{source:r.Icon.Music,tintColor:r.Color.Purple},accessories:t?.currentTrack?.isPlaying?[{text:"Playing",icon:{source:r.Icon.Play,tintColor:r.Color.Green}}]:[{text:"Paused",icon:{source:r.Icon.Pause,tintColor:r.Color.Orange}}]}),(0,d.jsx)(r.List.Item,{title:"Pending Commands",subtitle:`${t?.pendingCommandsCount||0} commands in queue`,icon:{source:r.Icon.Terminal,tintColor:r.Color.Yellow}})]})]})}
