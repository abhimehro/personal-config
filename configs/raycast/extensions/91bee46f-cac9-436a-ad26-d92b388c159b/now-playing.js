"use strict";var m=Object.create;var p=Object.defineProperty;var R=Object.getOwnPropertyDescriptor;var w=Object.getOwnPropertyNames;var h=Object.getPrototypeOf,x=Object.prototype.hasOwnProperty;var k=(e,a)=>{for(var r in a)p(e,r,{get:a[r],enumerable:!0})},u=(e,a,r,n)=>{if(a&&typeof a=="object"||typeof a=="function")for(let o of w(a))!x.call(e,o)&&o!==r&&p(e,o,{get:()=>a[o],enumerable:!(n=R(a,o))||n.enumerable});return e};var j=(e,a,r)=>(r=e!=null?m(h(e)):{},u(a||!e||!e.__esModule?p(r,"default",{value:e,enumerable:!0}):r,e)),S=e=>u(p({},"__esModule",{value:!0}),e);var D={};k(D,{default:()=>P});module.exports=S(D);var f=require("@raycast/api");var t=require("@raycast/api");var y=j(require("node:process"),1),c=require("node:util"),l=require("node:child_process"),b=(0,c.promisify)(l.execFile);async function i(e,{humanReadableOutput:a=!0}={}){if(y.default.platform!=="darwin")throw new Error("macOS only");let r=a?[]:["-ss"],{stdout:n}=await b("osascript",["-e",e,r]);return n.trim()}var v=require("@raycast/api");async function N(e){try{let r=(await i(`
        tell application "System Events"
          if exists (processes where name is "TIDAL") then
            return "true"
          else
            return "false"
          end if
        end tell
      `)).trim().toLowerCase()==="true";return!r&&!e?.silent&&await(0,t.showHUD)("Tidal: Not running \u274C"),r}catch(a){return console.error("Error checking if Tidal is running:",a),e?.silent||await(0,t.showHUD)("Tidal: Error checking if running \u274C"),!1}}async function d(e,a){if(await N(a))try{await e()}catch(n){console.error("Error running Tidal command:",n),await(0,t.showHUD)(`Tidal: Error running command! \u274C
Did you choose the right language in your settings?`)}}function O(){return(0,v.getPreferenceValues)()}function s(e){O().showMessages&&(0,t.showHUD)(e)}async function g(){let e=await i(`
      tell application "System Events"
        try
        tell process "TIDAL"
          set windowTitle to name of window 1
          return windowTitle
        end tell
        on error
          return "TIDAL"
        end try
      end tell`),a=e,r=e.replace(/(.{40}\S*?)(\s+|$)/g,`$1
`),n=e.length>20?e.slice(0,20)+"...":e;return{full:a,formatted:r,short:n}}async function P(){await d(async()=>{await(0,f.closeMainWindow)();let e=(await g()).full;e!==null&&e!=="TIDAL"?s(e):s("Now Playing is Not Available - Open Tidal")})}
