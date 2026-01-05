"use strict";var E=Object.create;var a=Object.defineProperty;var S=Object.getOwnPropertyDescriptor;var F=Object.getOwnPropertyNames;var k=Object.getPrototypeOf,x=Object.prototype.hasOwnProperty;var C=(t,e)=>()=>(e||t((e={exports:{}}).exports,e),e.exports),M=(t,e)=>{for(var r in e)a(t,r,{get:e[r],enumerable:!0})},f=(t,e,r,n)=>{if(e&&typeof e=="object"||typeof e=="function")for(let u of F(e))!x.call(t,u)&&u!==r&&a(t,u,{get:()=>e[u],enumerable:!(n=S(e,u))||n.enumerable});return t};var _=(t,e,r)=>(r=t!=null?E(k(t)):{},f(e||!t||!t.__esModule?a(r,"default",{value:t,enumerable:!0}):r,t)),q=t=>f(a({},"__esModule",{value:!0}),t);var m=C(c=>{"use strict";Object.defineProperty(c,"__esModule",{value:!0});var o=require("react"),A=function(){};function l(t,e,r){var n=o.useRef(A);o.useEffect(function(){n.current=t}),o.useEffect(function(){r&&(e===null||e===!1||n.current())},[r]),o.useEffect(function(){if(!(e===null||e===!1)){var u=function(){return n.current()},I=setInterval(u,e);return function(){return clearInterval(I)}}},[e])}c.default=l;c.useInterval=l});var j={};M(j,{default:()=>h});module.exports=q(j);var s=require("@raycast/api"),d=require("fs"),p=require("path"),v=require("react"),g=_(m()),b=require("react/jsx-runtime"),D=16,L=1e3;function h(){let[t,e]=(0,v.useState)(0);(0,g.default)(()=>{e(u=>(u+1)%D)},L);let r=R(t);return(0,b.jsx)(s.Detail,{markdown:`\`\`\`
${r}
\`\`\`

Starting square breathing \u{1FAB7}

Such cycles should be repeated for 1-3 minutes, but preferably 4-5 minutes. This technique is designed to help you relax after a long day, or before/after a challenging task or conversation.
`})}var i=new Map;function R(t){if(i.has(t))return i.get(t);let e=(0,p.resolve)(s.environment.assetsPath,"frames",`${t}.txt`),r=(0,d.readFileSync)(e,"utf8"),n=s.environment.textSize==="large"?$(r):r;return i.set(t,n),n}function $(t){return t.split(`
`).map(n=>n.replace(/^ {0,6}/,"")).join(`
`)}
