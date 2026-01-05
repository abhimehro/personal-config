"use strict";var w=Object.create;var g=Object.defineProperty;var F=Object.getOwnPropertyDescriptor;var b=Object.getOwnPropertyNames;var j=Object.getPrototypeOf,q=Object.prototype.hasOwnProperty;var P=(n,e)=>{for(var o in e)g(n,o,{get:e[o],enumerable:!0})},d=(n,e,o,l)=>{if(e&&typeof e=="object"||typeof e=="function")for(let a of b(e))!q.call(n,a)&&a!==o&&g(n,a,{get:()=>e[a],enumerable:!(l=F(e,a))||l.enumerable});return n};var f=(n,e,o)=>(o=n!=null?w(j(n)):{},d(e||!n||!n.__esModule?g(o,"default",{value:n,enumerable:!0}):o,n)),I=n=>d(g({},"__esModule",{value:!0}),n);var C={};P(C,{default:()=>A});module.exports=I(C);var t=require("@raycast/api"),$=require("@raycast/api"),u=f(require("fs")),p=f(require("path")),h=require("react"),r=require("react/jsx-runtime");function y(n){return p.default.basename(n,".json").split(/[-_]/).map(a=>a.charAt(0).toUpperCase()+a.slice(1)).join(" ")}function A(){let n=$.environment.supportPath,[e,o]=(0,h.useState)([]),l=()=>{let i=u.default.readdirSync(n).filter(c=>c.endsWith(".json"));o(i)};(0,h.useEffect)(()=>{l()},[n]);let a=async i=>{let c=p.default.join(n,i);await(0,t.confirmAlert)({title:"Delete File",message:`Are you sure you want to delete "${i}"?`,icon:t.Icon.Trash,primaryAction:{title:"Delete",style:t.Alert.ActionStyle.Destructive,onAction:()=>{u.default.unlinkSync(c),l()}}})};return(0,r.jsx)(t.List,{isShowingDetail:e.length!=0,children:e.length===0?(0,r.jsx)(t.List.EmptyView,{icon:t.Icon.MagnifyingGlass,title:"No Research",description:"Use @research in Raycast AI to get started"}):e.map(i=>{let c=p.default.join(n,i),D=u.default.readFileSync(c,"utf-8").split(`
`).filter(Boolean).map(s=>JSON.parse(s));return(0,r.jsx)(t.List.Item,{title:y(i),detail:(0,r.jsx)(t.List.Item.Detail,{markdown:`# ${y(i)}
\`${i}\`

${D.map(s=>{let N=s.learnings&&s.learnings.length>0?s.learnings.map(m=>`- ${m}`).join(`
`):"> No learnings",S=s.questions&&s.questions.length>0?s.questions.map(m=>`- ${m}`).join(`
`):"> No questions",T=s.goals&&s.goals.length>0?s.goals.map(m=>`- ${m}`).join(`
`):"> No goals";return`## Thought ${s.thoughtNumber}/${s.totalThoughts}

${s.thought}

**Learnings:**
${N}

**Questions:**
${S}

**Goals:**
${T}`}).join(`

`)}`}),actions:(0,r.jsxs)(t.ActionPanel,{children:[(0,r.jsx)(t.Action.ShowInFinder,{path:c,title:"Show File in Finder"}),(0,r.jsx)(t.Action,{title:"Delete File",icon:t.Icon.Trash,style:t.Action.Style.Destructive,onAction:async()=>{await a(i)}})]})},i)})})}
