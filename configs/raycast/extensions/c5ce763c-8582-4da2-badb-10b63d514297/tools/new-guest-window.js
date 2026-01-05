"use strict";var E=Object.create;var c=Object.defineProperty;var _=Object.getOwnPropertyDescriptor;var T=Object.getOwnPropertyNames;var A=Object.getPrototypeOf,R=Object.prototype.hasOwnProperty;var P=(e,t)=>{for(var n in t)c(e,n,{get:t[n],enumerable:!0})},h=(e,t,n,i)=>{if(t&&typeof t=="object"||typeof t=="function")for(let a of T(t))!R.call(e,a)&&a!==n&&c(e,a,{get:()=>t[a],enumerable:!(i=_(t,a))||i.enumerable});return e};var l=(e,t,n)=>(n=e!=null?E(A(e)):{},h(t||!e||!e.__esModule?c(n,"default",{value:e,enumerable:!0}):n,e)),C=e=>h(c({},"__esModule",{value:!0}),e);var M={};P(M,{default:()=>D});module.exports=C(M);var p=l(require("node:process"),1),m=require("node:util"),f=require("node:child_process"),I=(0,m.promisify)(f.execFile);async function u(e,{humanReadableOutput:t=!0,signal:n}={}){if(p.default.platform!=="darwin")throw new Error("macOS only");let i=t?[]:["-ss"],a={};n&&(a.signal=n);let{stdout:S}=await I("osascript",["-e",e,i],a);return S.trim()}var o=require("@raycast/api");var s=l(require("react")),r=require("@raycast/api");var g=require("react/jsx-runtime");var $=l(require("fs"));var d=l(require("path"));var O=require("@raycast/api"),U=()=>{if(!process.env.HOME)throw new Error("$HOME environment variable is not set.");return d.default.join(process.env.HOME,"Library")};var b=()=>d.default.join(U(),...y);var N=()=>{try{let e=b(),t=$.default.readFileSync(e,"utf-8"),n=JSON.parse(t).profile.info_cache;return n?Object.keys(n)[0]:"Default"}catch{return"Default"}};var y=["Application Support","Google","Chrome","Local State"],L=N();var w="Google Chrome not installed";var k=async()=>{if(await o.LocalStorage.getItem("is-installed"))return;if(await u(`
set isInstalled to false
try
    do shell script "osascript -e 'exists application \\"Google Chrome\\"'"
    set isInstalled to true
end try

return isInstalled`)==="false")throw new Error(w);o.LocalStorage.setItem("is-installed",!0)};async function x(){await k(),await u(`
    do shell script "open -na 'Google Chrome' --args --guest"
  `)}async function v(e){await k(),await u(`
    set link to quoted form of "${e}"
    do shell script "open -na 'Google Chrome' --args --guest " & link
  `)}async function D(e){return e.website?(await v(e.website),`Opening new guest window to ${e.website}`):(await x(),"Opening new guest window")}
