"use strict";var T=Object.create;var l=Object.defineProperty;var A=Object.getOwnPropertyDescriptor;var R=Object.getOwnPropertyNames;var P=Object.getPrototypeOf,C=Object.prototype.hasOwnProperty;var I=(e,t)=>{for(var n in t)l(e,n,{get:t[n],enumerable:!0})},p=(e,t,n,c)=>{if(t&&typeof t=="object"||typeof t=="function")for(let a of R(t))!C.call(e,a)&&a!==n&&l(e,a,{get:()=>t[a],enumerable:!(c=A(t,a))||c.enumerable});return e};var u=(e,t,n)=>(n=e!=null?T(P(e)):{},p(t||!e||!e.__esModule?l(n,"default",{value:e,enumerable:!0}):n,e)),O=e=>p(l({},"__esModule",{value:!0}),e);var W={};I(W,{default:()=>E});module.exports=O(W);var i=require("@raycast/api");var m=u(require("node:process"),1),g=require("node:util"),d=require("node:child_process"),U=(0,g.promisify)(d.execFile);async function f(e,{humanReadableOutput:t=!0,signal:n}={}){if(m.default.platform!=="darwin")throw new Error("macOS only");let c=t?[]:["-ss"],a={};n&&(a.signal=n);let{stdout:_}=await U("osascript",["-e",e,c],a);return _.trim()}var o=require("@raycast/api");var s=u(require("react")),r=require("@raycast/api");var b=require("react/jsx-runtime");var w=u(require("fs"));var h=u(require("path"));var L=require("@raycast/api"),N=()=>{if(!process.env.HOME)throw new Error("$HOME environment variable is not set.");return h.default.join(process.env.HOME,"Library")};var y=()=>h.default.join(N(),...$);var M=()=>{try{let e=y(),t=w.default.readFileSync(e,"utf-8"),n=JSON.parse(t).profile.info_cache;return n?Object.keys(n)[0]:"Default"}catch{return"Default"}};var $=["Application Support","Google","Chrome","Local State"],D=M();var k="Google Chrome not installed";var x=async()=>{if(await o.LocalStorage.getItem("is-installed"))return;if(await f(`
set isInstalled to false
try
    do shell script "osascript -e 'exists application \\"Google Chrome\\"'"
    set isInstalled to true
end try

return isInstalled`)==="false")throw new Error(k);o.LocalStorage.setItem("is-installed",!0)};async function v(e){await x(),await f(`
    set link to quoted form of "${e}"
    do shell script "open -na 'Google Chrome' --args --guest " & link
  `)}async function S(){return await x(),await f(`
    tell application "Google Chrome"
      try
        return URL of active tab of front window
      on error
        return ""
      end try
    end tell
  `)}async function E(){try{await(0,i.closeMainWindow)();let e=await S();if(!e||e===""){await(0,i.showHUD)("No active tab URL found to open in guest window");return}await v(e)}catch{await(0,i.showHUD)("\u274C Failed opening current tab in Guest window")}}
